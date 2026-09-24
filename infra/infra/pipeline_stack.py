# infra/infra/pipeline_stack.py
from aws_cdk import (
    Stack, Duration,
    aws_ecr_assets as ecr_assets,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_secretsmanager as sm,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

# Match your laptop (run `uname -m`): x86_64 -> X86_64 and LINUX_AMD64; arm64 or aarch64 -> ARM_64 and LINUX_ARM64
ARCH = lambda_.Architecture.ARM_64
PLATFORM = ecr_assets.Platform.LINUX_ARM64


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, media, table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        telegram = sm.Secret.from_secret_name_v2(self, "Telegram", "clip/telegram")

        make_clip_fn = lambda_.DockerImageFunction(
            self, "MakeClipFn",
            code=lambda_.DockerImageCode.from_image_asset("../services/make_clip", platform=PLATFORM),
            architecture=ARCH,
            memory_size=3008,
            timeout=Duration.minutes(5),
        )
        media.grant_read_write(make_clip_fn)

        notify_fn = lambda_.Function(
            self, "NotifyFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="app.handler",
            code=lambda_.Code.from_asset("../services/notify"),
            timeout=Duration.seconds(30),
            environment={"BUCKET": media.bucket_name, "SECRET_ID": "clip/telegram"},
        )
        media.grant_read(notify_fn)
        telegram.grant_read(notify_fn)

        video_id = sfn.JsonPath.string_at("$$.Execution.Name")

        start_transcribe = tasks.CallAwsService(
            self, "StartTranscription",
            service="transcribe",
            action="startTranscriptionJob",
            iam_resources=["*"],
            parameters={
                "TranscriptionJobName": video_id,
                "LanguageCode": "en-US",
                "Media": {"MediaFileUri": sfn.JsonPath.format(
                    "s3://{}/{}",
                    sfn.JsonPath.string_at("$.detail.bucket.name"),
                    sfn.JsonPath.string_at("$.detail.object.key"),
                )},
                "OutputBucketName": media.bucket_name,
                "OutputKey": sfn.JsonPath.format("transcripts/{}/", video_id),
                "Settings": {"ShowSpeakerLabels": True, "MaxSpeakerLabels": 4},
                "Subtitles": {"Formats": ["srt"]},
            },
            result_path=sfn.JsonPath.DISCARD,
        )
        wait = sfn.Wait(self, "Wait30s", time=sfn.WaitTime.duration(Duration.seconds(30)))
        get_transcribe = tasks.CallAwsService(
            self, "GetTranscription",
            service="transcribe",
            action="getTranscriptionJob",
            iam_resources=["*"],
            parameters={"TranscriptionJobName": video_id},
            result_selector={"status": sfn.JsonPath.string_at("$.TranscriptionJob.TranscriptionJobStatus")},
            result_path="$.transcript",
        )
        make_clip = tasks.LambdaInvoke(
            self, "MakeRoughClip",
            lambda_function=make_clip_fn,
            payload=sfn.TaskInput.from_object({
                "bucket": sfn.JsonPath.string_at("$.detail.bucket.name"),
                "key": sfn.JsonPath.string_at("$.detail.object.key"),
                "video_id": video_id,
            }),
            result_selector={"preview_key": sfn.JsonPath.string_at("$.Payload.preview_key")},
            result_path="$.clip",
        )
        send = tasks.LambdaInvoke(
            self, "SendToPhone",
            lambda_function=notify_fn,
            payload=sfn.TaskInput.from_object({
                "preview_key": sfn.JsonPath.string_at("$.clip.preview_key"),
                "text": "Rough clip ready",
            }),
            result_path=sfn.JsonPath.DISCARD,
        )

        definition = start_transcribe.next(wait).next(get_transcribe).next(
            sfn.Choice(self, "TranscriptReady?")
            .when(sfn.Condition.string_equals("$.transcript.status", "COMPLETED"), make_clip.next(send))
            .when(sfn.Condition.string_equals("$.transcript.status", "FAILED"), sfn.Fail(self, "TranscriptionFailed"))
            .otherwise(wait)
        )

        machine = sfn.StateMachine(
            self, "Pipeline",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(2),
        )
        media.grant_read_write(machine)  # Transcribe reads and writes S3 as this role

        events.Rule(
            self, "OnRawUpload",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [media.bucket_name]},
                    "object": {"key": [{"prefix": "raw/"}]},
                },
            ),
            targets=[targets.SfnStateMachine(machine)],
        )