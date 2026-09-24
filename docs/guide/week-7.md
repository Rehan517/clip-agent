> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## Week 7: Face tracking and security hardening

By Sunday, final renders follow the speaker's face, every deploy comes from GitHub with short-lived credentials, and you can prove that no agent can publish. This is the week that makes the project read as security engineering, not just a demo.

**Files this week.** Create and Replace rows are whole files. Change rows show only the new lines, and the `#` comments in those boxes say where each part goes; running `/step` with the week and step name in Claude Code places them with you.

| File | What you do | Step |
| --- | --- | --- |
| `services/render_preview/models/` | Download the YuNet face model into this new folder | Follow the speaker |
| `services/render_preview/reframe.py` | Create | Follow the speaker |
| `services/render_preview/app.py` | Change: import `reframe` and replace the `vf = ...` line | Follow the speaker |
| `services/render_preview/Dockerfile` | Replace with the version shown | Follow the speaker |
| `main.py` of the Moment Finder, Compliance and Producer agents | Change: pass the guardrail to `BedrockModel` | Guardrails on untrusted text |
| `infra/infra/ci_stack.py` | Create | Deploy from GitHub without stored keys |
| `infra/app.py` | Change: import `CiStack` and add the `CiStack(...)` line | Deploy from GitHub without stored keys |
| `.github/workflows/deploy.yml` | Create (make the `.github/workflows` folders first) | Deploy from GitHub without stored keys |
| `infra/infra/storage_stack.py` | Change: add the evidence bucket | Tamper-proof evidence and a threat model |
| `services/metrics/app.py` | Change: write evidence to the new bucket | Tamper-proof evidence and a threat model |
| `docs/threat-model.md` | Create | Tamper-proof evidence and a threat model |
| `services/ops_tools/app.py` and `services/ops_tools/tools.json` | Create | A Producer agent behind a Cedar policy |
| `services/notify/producer_relay.py` | Create | A Producer agent behind a Cedar policy |
| `services/notify/webhook.py` | Change: route plain messages to the relay | A Producer agent behind a Cedar policy |
| `agents/clipagents/ops_policy.cedar` | Create | A Producer agent behind a Cedar policy |
| `agents/clipagents/app/Producer/main.py` | Replace the file `agentcore add agent` makes | A Producer agent behind a Cedar policy |
| `infra/infra/pipeline_stack.py` | Change: pass in the evidence bucket, then add the tools and relay functions | Tamper-proof evidence; A Producer agent |

### Follow the speaker (about 5 hours)

- [ ] Download OpenCV's YuNet face detector (`face_detection_yunet_2023mar.onnx` from the opencv\_zoo repository on GitHub) into `services/render_preview/models/`.
- [ ] Add `reframe.py`. It samples four frames a second, finds the biggest face, and holds the crop still until the face moves a lot, like a camera operator cutting between shots:

```python
# services/render_preview/reframe.py
import glob
import os
import subprocess
import tempfile

import cv2

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "face_detection_yunet_2023mar.onnx")


def source_size(src):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", src],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    width, height = out.split(",")[:2]
    return int(width), int(height)


def face_track(src, start, duration, fps=4):
    """Horizontal centre of the biggest face (0 to 1) in each sampled frame, or None."""
    track = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", src, "-t", f"{duration:.2f}",
             "-vf", f"fps={fps},scale=640:-2", f"{tmp}/f_%05d.jpg"],
            check=True, capture_output=True,
        )
        detector = None
        for path in sorted(glob.glob(f"{tmp}/f_*.jpg")):
            img = cv2.imread(path)
            h, w = img.shape[:2]
            if detector is None:
                detector = cv2.FaceDetectorYN.create(MODEL, "", (w, h), 0.7)
            _, faces = detector.detect(img)
            if faces is None or len(faces) == 0:
                track.append(None)
            else:
                x, _, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
                track.append(float(x + fw / 2) / w)
    return track


def crop_x_expression(track, fps, src_w, src_h, dead_zone=0.08, min_shot=1.5):
    """Hold the crop steady and only 'cut' when the face moves a lot, like a camera operator.
    Returns an FFmpeg expression for the crop's x position over time t."""
    crop_w = int(src_h * 9 / 16) // 2 * 2
    to_x = lambda cx: int(min(max(cx * src_w - crop_w / 2, 0), src_w - crop_w))
    shots = []  # (start time, x)
    current = None
    for i, cx in enumerate(track):
        t = i / fps
        if cx is None:
            continue
        if current is None or (abs(cx - current) > dead_zone and t - shots[-1][0] >= min_shot):
            current = cx
            shots.append((t, to_x(cx)))
    if not shots:
        return crop_w, f"{(src_w - crop_w) // 2}"  # no faces found: centre crop
    expr = str(shots[-1][1])
    for k in range(len(shots) - 2, -1, -1):
        expr = f"if(lt(t,{shots[k + 1][0]:.2f}),{shots[k][1]},{expr})"
    return crop_w, expr
```

- [ ] Use it for final renders in `app.py`. Import it, then replace the `vf = ...` line:

```python
from reframe import crop_x_expression, face_track, source_size

    if final:  # follow the speaker's face; previews keep the cheap centre crop
        src_w, src_h = source_size(src)
        crop_w, x_expr = crop_x_expression(face_track(src, start, end - start), 4, src_w, src_h)
        crop = f"crop={crop_w}:ih:'{x_expr}':0"
    else:
        crop = "crop=ih*9/16:ih"
    vf = f"{crop},scale={size},subtitles={ass_path}:fontsdir={FONTS}"
```

- [ ] Update the Dockerfile:

```dockerfile
FROM mwader/static-ffmpeg:9.0 AS ffmpeg
FROM public.ecr.aws/lambda/python:3.12
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
RUN pip install --no-cache-dir opencv-python-headless
COPY fonts/ ${LAMBDA_TASK_ROOT}/fonts/
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY app.py captions.py index.py reframe.py ${LAMBDA_TASK_ROOT}/
CMD ["app.handler"]
```

- [ ] Compare five face-tracked clips against their centre-cropped previews, and tune `dead_zone` if the frame jumps too often.

### Guardrails on untrusted text (1 hour)

- [ ] In the Bedrock console, create a guardrail with the prompt attack filter set to High, then publish version 1.
- [ ] Pass it to the agents that read strangers' words (Moment Finder, Compliance, Producer): `BedrockModel(..., guardrail_id="YOUR_ID", guardrail_version="1")` ([Strands](https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/)).

### Deploy from GitHub without stored keys (about 2 hours)

- [ ] Add `infra/infra/ci_stack.py`, register it in `app.py` as `CiStack(app, "ClipCi", repo="YOUR_GITHUB_USERNAME/clip-agent", env=env)`, and deploy it once from your laptop.

```python
# infra/infra/ci_stack.py
from aws_cdk import CfnOutput, Duration, Stack, aws_iam as iam
from constructs import Construct


class CiStack(Stack):
    """Lets GitHub Actions deploy with short-lived credentials. Deploy this one stack from your laptop."""

    def __init__(self, scope: Construct, construct_id: str, *, repo: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        provider = iam.OpenIdConnectProvider(
            self, "GitHub",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )
        role = iam.Role(
            self, "DeployRole",
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                    # Only the main branch of your repo can deploy
                    "StringLike": {"token.actions.githubusercontent.com:sub": f"repo:{repo}:ref:refs/heads/main"},
                },
            ),
            max_session_duration=Duration.hours(1),
        )
        # CDK deploys through its bootstrap roles, so this role only needs to assume them
        role.add_to_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"], resources=[f"arn:aws:iam::{self.account}:role/cdk-*"],
        ))
        CfnOutput(self, "DeployRoleArn", value=role.role_arn)
```

- [ ] Save the `DeployRoleArn` output as a GitHub Actions secret named `AWS_DEPLOY_ROLE_ARN`, then add the workflow:

```yaml
# .github/workflows/deploy.yml
name: deploy
on:
  push:
    branches: [main]
permissions:
  id-token: write   # lets the job request an OIDC token
  contents: read
jobs:
  deploy:
    runs-on: ubuntu-latest   # matches x86_64 Lambdas; for ARM64 Lambdas use ubuntu-24.04-arm
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: us-east-1
      - run: npm install -g aws-cdk
      - run: pip install -r infra/requirements.txt
      - run: cd infra && cdk deploy ClipStorage ClipPipeline --require-approval never
```

The `configure-aws-credentials@v6` OIDC pattern comes from [its README](https://github.com/aws-actions/configure-aws-credentials).

### Tamper-proof evidence and a threat model (about 2 hours)

- [ ] Add a write-once evidence bucket to the storage stack, pass it into the pipeline stack, and give the metrics function `grant_put` on it:

```python
        # Write-once evidence for payout disputes: objects can't be changed or deleted for 90 days
        self.evidence = s3.Bucket(
            self, "Evidence",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            object_lock_enabled=True,
            object_lock_default_retention=s3.ObjectLockRetention.governance(Duration.days(90)),
            removal_policy=RemovalPolicy.RETAIN,
        )
```

- [ ] In `metrics/app.py`, write evidence to that bucket with `Bucket=os.environ["EVIDENCE_BUCKET"]` and `ChecksumAlgorithm="SHA256"`, because Object Lock buckets insist on a checksum.
- [ ] Write `docs/threat-model.md`: a STRIDE table covering prompt injection, stolen tokens, runaway spend, account bans, data exposure and payout disputes, using the controls from the architecture doc.

### A Producer agent behind a Cedar policy (about 5 hours)

Message your bot in plain English ("what's pending?", "how did clip X do?") and a Producer agent answers through AgentCore Gateway tools. One tool, `publish_now`, exists only so you can prove the policy blocks it.

- [ ] Create `services/ops_tools/app.py` and `tools.json`. Gateway calls one Lambda for every tool and passes the tool's name in the context ([AWS](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html)):

```python
# services/ops_tools/app.py
import json
import os

import boto3
from boto3.dynamodb.conditions import Attr, Key

table = boto3.resource("dynamodb").Table(os.environ["TABLE"])


def handler(event, context):
    """AgentCore Gateway calls this for every Producer tool. The event holds the tool's arguments."""
    full_name = context.client_context.custom["bedrockAgentCoreToolName"]  # "Ops___list_pending"
    tool = full_name.split("___", 1)[1]

    if tool == "list_pending":
        items = table.scan(FilterExpression=Attr("status").eq("PENDING"))["Items"]
        return {"pending": [{"clip_id": i["pk"][5:], "title": json.loads(i["candidate"])["title"]} for i in items]}

    if tool == "clip_views":
        items = table.query(
            KeyConditionExpression=Key("pk").eq(f"CLIP#{event['clip_id']}") & Key("sk").begins_with("METRIC#")
        )["Items"]
        return {"snapshots": [{"when": i["sk"], "views": int(i["views"])} for i in items]}

    if tool == "publish_now":
        # The Cedar policy should stop this call at the Gateway. If this line ever logs, fix the policy.
        print("ALERT: publish_now reached the Lambda")
        return {"error": "Publishing only happens through the approval pipeline."}

    return {"error": f"Unknown tool {tool}"}
```

```json
[
  {
    "name": "list_pending",
    "description": "List clips waiting for Rehan's approval",
    "inputSchema": {"type": "object", "properties": {}}
  },
  {
    "name": "clip_views",
    "description": "Daily view counts recorded for one clip",
    "inputSchema": {
      "type": "object",
      "properties": {"clip_id": {"type": "string", "description": "The clip ID from Telegram"}},
      "required": ["clip_id"]
    }
  },
  {
    "name": "publish_now",
    "description": "Publish a clip immediately",
    "inputSchema": {
      "type": "object",
      "properties": {"clip_id": {"type": "string"}},
      "required": ["clip_id"]
    }
  }
]
```

- [ ] In CDK, add the tools function with read-only table access, output its ARN, and add a relay function (`services/notify/producer_relay.py`, below) that the webhook invokes asynchronously. API Gateway gives the webhook 30 seconds, and an agent can take longer.

```python
        ops_fn = lambda_.Function(
            self, "OpsToolsFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="app.handler",
            code=lambda_.Code.from_asset("../services/ops_tools"),
            timeout=Duration.seconds(30),
            environment={"TABLE": table.table_name},
        )
        table.grant_read_data(ops_fn)  # read-only: the Producer's tools can't change anything
        CfnOutput(self, "OpsToolsArn", value=ops_fn.function_arn)

        relay_fn = lambda_.Function(
            self, "ProducerRelayFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="producer_relay.handler",
            code=lambda_.Code.from_asset("../services/notify"),
            timeout=Duration.minutes(5),
            environment={**telegram_env, "PRODUCER_ARN": PRODUCER_ARN},
        )
        telegram.grant_read(relay_fn)
        relay_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeAgentRuntime"], resources=[PRODUCER_ARN, f"{PRODUCER_ARN}/*"],
        ))
        webhook_fn.add_environment("PRODUCER_RELAY", relay_fn.function_name)
        relay_fn.grant_invoke(webhook_fn)
```

```python
# services/notify/producer_relay.py
import json
import os
import uuid

import boto3
from botocore.config import Config

from app import cfg, telegram

agentcore = boto3.client("bedrock-agentcore", config=Config(read_timeout=900, retries={"max_attempts": 1}))


def handler(event, context):
    """Runs asynchronously, so Telegram's webhook gets its quick 200 while the agent thinks."""
    resp = agentcore.invoke_agent_runtime(
        agentRuntimeArn=os.environ["PRODUCER_ARN"],
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps({"prompt": event["prompt"]}).encode(),
    )
    reply = json.loads(resp["response"].read())["reply"]
    telegram("sendMessage", {"chat_id": cfg()["chat_id"], "text": reply[:4000]})
    return {"ok": True}
```

- [ ] In `webhook.py`, add `lambda_client = boto3.client("lambda")`, then route plain messages to the relay:

```python
    text = message.get("text", "")
    if str(message.get("chat", {}).get("id")) == str(cfg()["chat_id"]) and text:
        if text.startswith("/views"):
            return log_views(text)
        # Anything else is a question for the Producer agent, answered asynchronously
        lambda_client.invoke(FunctionName=os.environ["PRODUCER_RELAY"], InvocationType="Event",
                             Payload=json.dumps({"prompt": text}))
        return {"statusCode": 200, "body": "ok"}
```

- [ ] Create the Producer agent, its gateway, the tools target and a policy engine with the AgentCore CLI ([AWS](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-getting-started.html)):

```bash
agentcore add agent            # name it Producer
agentcore add gateway --name OpsGateway --authorizer-type NONE --runtimes Producer
agentcore add gateway-target --name Ops --type lambda-function-arn \
  --lambda-arn OPS_TOOLS_ARN --tool-schema-file ../../services/ops_tools/tools.json --gateway OpsGateway
agentcore add policy-engine --name OpsPolicy --attach-to-gateways OpsGateway --attach-mode ENFORCE
agentcore deploy
agentcore status               # copy the gateway ARN and URL, and the Producer's runtime ARN
```

- [ ] Write `ops_policy.cedar` with your gateway ARN, then `agentcore add policy --name ReadOnly --engine OpsPolicy --source ops_policy.cedar` and deploy again. Everything not permitted is denied, and the explicit forbid makes the intent obvious to a reader:

```cedar
permit(principal,
  action in [AgentCore::Action::"Ops___list_pending", AgentCore::Action::"Ops___clip_views"],
  resource == AgentCore::Gateway::"YOUR_GATEWAY_ARN");

forbid(principal,
  action == AgentCore::Action::"Ops___publish_now",
  resource == AgentCore::Gateway::"YOUR_GATEWAY_ARN");
```

- [ ] Replace the Producer's `main.py`, setting `GATEWAY_URL` to your gateway's MCP URL:

```python
# agents/clipagents/app/Producer/main.py
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

GATEWAY_URL = os.environ.get("GATEWAY_URL", "https://YOUR-GATEWAY-ID.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
app = BedrockAgentCoreApp()

SYSTEM = """You are Rehan's clipping producer. Answer questions about pending clips and results
using your tools, briefly and with numbers. You cannot publish anything: clips are only posted
after Rehan approves them in Telegram. If a tool call is denied, say so plainly."""


@app.entrypoint
def invoke(payload, context):
    gateway = MCPClient(url=GATEWAY_URL)
    with gateway:
        agent = Agent(
            model=BedrockModel(model_id="us.anthropic.claude-sonnet-5", region_name="us-east-1"),
            system_prompt=SYSTEM,
            tools=gateway.list_tools_sync(),
        )
        result = agent(payload["prompt"])
    return {"reply": str(result)}


if __name__ == "__main__":
    app.run()
```

- [ ] Before you call this finished, switch the gateway from `NONE` to `CUSTOM_JWT` with a Cognito user pool, and have the Producer send a bearer token (`MCPClient(url=..., headers={"Authorization": f"Bearer {token}"})`). A `NONE` gateway answers anyone who finds its URL.

### Prove the guarantees (1 hour)

- [ ] Ask the bot to "publish clip X now". The reply should say it was denied, and the ops Lambda's logs should contain no `ALERT` line.
- [ ] Check that no agent role can call the publisher, using the IAM policy simulator:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/MOMENT_FINDER_ROLE_NAME \
  --action-names lambda:InvokeFunction states:SendTaskSuccess \
  --resource-arns PUBLISH_FN_ARN
# every EvalDecision should read implicitDeny
```

**Done when:** final clips follow faces, `git push` deploys, the `publish_now` test is denied at the gateway, and the simulator shows implicit denies.

**Escape hatch:** if the Gateway or policy setup stalls, keep the Producer read-only with in-process tools and note the Cedar policy as next work. The IAM simulator test still proves your agents can't publish.
