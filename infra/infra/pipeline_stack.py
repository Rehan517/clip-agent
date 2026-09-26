# infra/infra/pipeline_stack.py
from aws_cdk import (
    Stack, Duration,
    aws_ecr_assets as ecr_assets,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_secretsmanager as sm,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

# Match your laptop (run `uname -m`): x86_64 -> X86_64 and LINUX_AMD64; arm64 or aarch64 -> ARM_64 and LINUX_ARM64
ARCH = lambda_.Architecture.ARM_64
PLATFORM = ecr_assets.Platform.LINUX_ARM64

TRANSCRIPT_KB_ID = "ATIZYTNR7O"  # check: copy from Bedrock -> Knowledge bases
TRANSCRIPT_DS_ID = "VM0HHOYNV1"  # check: copy from the knowledge base's data source
MOMENT_FINDER_ARN = "arn:aws:bedrock-agentcore:us-east-1:730763715981:runtime/clipagents_MomentFinder-ncxhMj8xwv"
AGENT_ROLE_NAME = "AgentCore-clipagents-defa-ApplicationAgentMomentFin-Jv4uxv6uL3bP"  # AgentCore console -> MomentFinder runtime


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

        # ---- NEW: prepare transcript Lambda ----
        prepare_fn = lambda_.Function(
            self, "PrepareTranscriptFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="app.handler",
            code=lambda_.Code.from_asset("../services/prepare_transcript"),
            memory_size=1024,
            timeout=Duration.minutes(10),
            environment={
                "BUCKET": media.bucket_name,
                "TRANSCRIPT_KB_ID": TRANSCRIPT_KB_ID,
                "TRANSCRIPT_DS_ID": TRANSCRIPT_DS_ID,
            },
        )
        media.grant_read_write(prepare_fn)
        prepare_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{TRANSCRIPT_KB_ID}"],
        ))
        prepare_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{self.account}:inference-profile/*"],
        ))

        # ---- NEW: find moments Lambda (calls the MomentFinder agent) ----
        find_fn = lambda_.Function(
            self, "FindMomentsFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="app.handler",
            code=lambda_.Code.from_asset("../services/find_moments"),
            timeout=Duration.minutes(15),
            environment={
                "BUCKET": media.bucket_name,
                "TABLE": table.table_name,
                "TRANSCRIPT_KB_ID": TRANSCRIPT_KB_ID,
                "MOMENT_FINDER_ARN": MOMENT_FINDER_ARN,
            },
        )
        table.grant_read_write_data(find_fn)
        find_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeAgentRuntime"],
            resources=[MOMENT_FINDER_ARN, f"{MOMENT_FINDER_ARN}/*"],
        ))

        # Let the agent's own role read transcripts and query the knowledge base
        agent_role = iam.Role.from_role_name(self, "MomentFinderRole", AGENT_ROLE_NAME)
        iam.Policy(
            self, "MomentFinderDataAccess",
            roles=[agent_role],
            statements=[
                iam.PolicyStatement(actions=["s3:GetObject"], resources=[media.arn_for_objects("transcripts/*")]),
                iam.PolicyStatement(
                    actions=["bedrock:Retrieve"],
                    resources=[f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{TRANSCRIPT_KB_ID}"],
                ),
            ],
        )

        video_id = sfn.JsonPath.string_at("$$.Execution.Name")

        # ---- NEW: raw/<campaign_id>/<file>.mp4 -> <campaign_id> ----
        campaign_id = sfn.JsonPath.array_get_item(
            sfn.JsonPath.string_split(sfn.JsonPath.string_at("$.detail.object.key"), "/"), 1
        )

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

        # ---- NEW: prepare + find steps ----
        prepare = tasks.LambdaInvoke(
            self, "PrepareTranscript",
            lambda_function=prepare_fn,
            payload=sfn.TaskInput.from_object({"video_id": video_id, "campaign_id": campaign_id}),
            result_path=sfn.JsonPath.DISCARD,
        )
        # Only one ingestion job can run per data source, so wait and retry if one is busy
        prepare.add_retry(errors=["ConflictException"], interval=Duration.seconds(60), max_attempts=5)
        find = tasks.LambdaInvoke(
            self, "FindMoments",
            lambda_function=find_fn,
            payload=sfn.TaskInput.from_object({"video_id": video_id, "campaign_id": campaign_id}),
            result_selector={"candidates": sfn.JsonPath.list_at("$.Payload.candidates")},
            result_path="$.moments",
        )

        make_clip = tasks.LambdaInvoke(
            self, "MakeRoughClip",
            lambda_function=make_clip_fn,
            payload=sfn.TaskInput.from_object({
                "bucket": sfn.JsonPath.string_at("$.detail.bucket.name"),
                "key": sfn.JsonPath.string_at("$.detail.object.key"),
                "video_id": video_id,
                "start": sfn.JsonPath.number_at("$.moments.candidates[0].start"),  # NEW
                "end": sfn.JsonPath.number_at("$.moments.candidates[0].end"),      # NEW
            }),
            result_selector={"preview_key": sfn.JsonPath.string_at("$.Payload.preview_key")},
            result_path="$.clip",
        )
        send = tasks.LambdaInvoke(
            self, "SendToPhone",
            lambda_function=notify_fn,
            payload=sfn.TaskInput.from_object({
                "preview_key": sfn.JsonPath.string_at("$.clip.preview_key"),
                "text": sfn.JsonPath.string_at("$.moments.candidates[0].title"),  # CHANGED
            }),
            result_path=sfn.JsonPath.DISCARD,
        )

        definition = start_transcribe.next(wait).next(get_transcribe).next(
            sfn.Choice(self, "TranscriptReady?")
            .when(sfn.Condition.string_equals("$.transcript.status", "COMPLETED"),
                  prepare.next(find).next(make_clip).next(send))  # CHANGED
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