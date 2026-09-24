> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## Week 6: The learning loop

By Sunday, the system records views every day, learns your taste from every tap, and lets the Moment Finder search what happens on screen and study your past winners. A weekly report reaches Telegram before your check-in.

If time runs short, build in this order: view tracking (it protects your earnings), memory, the performance library, then the video index.

**Files this week.** Create and Replace rows are whole files. Change rows show only the new lines, and the `#` comments in those boxes say where each part goes; running `/step` with the week and step name in Claude Code places them with you.

| File | What you do | Step |
| --- | --- | --- |
| `services/notify/publish.py` | Change: add `find_value()`, move the `urls` line above `put_item`, and store two more fields | Track views every day |
| `services/metrics/app.py` | Create | Track views every day |
| `scripts/create_memory.py` | Create, then run it once | Learn your taste with AgentCore Memory |
| `services/notify/webhook.py` | Replace with the new version | Learn your taste with AgentCore Memory |
| `agents/clipagents/app/MomentFinder/main.py` | Change: a memory client and `preferences()` first, then two video tools in `make_tools` | Learn your taste; Video index with Marengo |
| `agents/clipagents/app/Analyst/main.py` | Replace the file `agentcore add agent` makes | Performance library and weekly report |
| `services/notify/weekly.py` | Create | Performance library and weekly report |
| `services/prepare_transcript/app.py` | Change: ask for a `potential` score in each chapter | Video index with Marengo |
| `services/render_preview/index.py` | Create, then add it to the Dockerfile's last `COPY` line | Video index with Marengo |
| `services/find_moments/app.py` | Change: two more fields in the agent's payload | Video index with Marengo |
| `infra/infra/pipeline_stack.py` | Change: new constants, settings, permissions and a new step, each headed by a `#` comment | CDK changes |

### Track views every day (about 4 hours)

- [ ] Create a YouTube Data API key: Google Cloud console, new project, enable YouTube Data API v3, then Credentials, API key. Restrict the key to that API. A stats lookup costs 1 unit of the 10,000-unit daily quota.
- [ ] Store the keys:

```bash
aws secretsmanager create-secret --name clip/metrics \
  --secret-string '{"youtube_api_key":"...","uploadpost_api_key":"..."}'
```

- [ ] Make `publish.py` save each post's URL and platform post ID. Add this helper, and move the `urls` line above the `put_item`, which gains two fields:

```python
def find_value(obj, name):
    """First value stored under `name` anywhere in the response, such as the platform's post_id."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == name and isinstance(v, (str, int)):
                return v
            found = find_value(v, name)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_value(v, name)
            if found is not None:
                return found
    return None

# In handler, replacing the put_item:
        urls = list(dict.fromkeys(find_urls(result)))
        table.put_item(Item={
            "pk": f"CLIP#{event['clip_id']}", "sk": f"POST#{platform}",
            "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "url": urls[0] if urls else "",
            "post_id": str(find_value(result, "post_id") or ""),
            "response": json.dumps(result),
        })
```

- [ ] Create `services/metrics/app.py`. It snapshots every post younger than 8 days and keeps each raw API response in S3 as evidence for payout disputes:

```python
# services/metrics/app.py
import datetime
import json
import os
import re
import urllib.request

import boto3
from boto3.dynamodb.conditions import Attr

s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")
table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
BUCKET = os.environ["BUCKET"]


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def first_number(obj, words=("view", "play")):
    """Find the first view-like count anywhere in an API response."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and any(w in k.lower() for w in words):
                return int(v)
            found = first_number(v, words)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = first_number(v, words)
            if found is not None:
                return found
    return None


def youtube_views(url, api_key):
    video_id = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{11})", url).group(1)
    data = get_json(f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={api_key}")
    return data, int(data["items"][0]["statistics"].get("viewCount", 0))


def handler(event, context):
    keys = json.loads(secrets.get_secret_value(SecretId="clip/metrics")["SecretString"])
    now = datetime.datetime.now(datetime.timezone.utc)
    since = (now - datetime.timedelta(days=8)).isoformat()
    posts = table.scan(
        FilterExpression=Attr("sk").begins_with("POST#") & Attr("posted_at").gte(since)
    )["Items"]
    for post in posts:
        platform = post["sk"].split("#", 1)[1]
        url, post_id = post.get("url"), post.get("post_id")
        try:
            if platform == "youtube" and url:
                raw, views = youtube_views(url, keys["youtube_api_key"])
            elif post_id:
                raw = get_json(
                    f"https://api.upload-post.com/api/uploadposts/post-analytics/{post_id}",
                    {"Authorization": f"Apikey {keys['uploadpost_api_key']}"},
                )
                views = first_number(raw)
            else:
                continue  # TikTok drafts you posted by hand: log their views with /views in Telegram
        except Exception as err:  # one bad post shouldn't stop the rest
            print(f"metrics failed for {post['pk']} {platform}: {err}")
            continue
        age_days = (now - datetime.datetime.fromisoformat(post["posted_at"])).days
        table.put_item(Item={
            "pk": post["pk"], "sk": f"METRIC#{platform}#d{age_days}",
            "views": views or 0, "checked_at": now.isoformat(),
        })
        # Raw API responses are your evidence if a campaign disputes the count
        s3.put_object(
            Bucket=BUCKET, Key=f"evidence/{post['pk'][5:]}/{platform}/{now:%Y%m%dT%H%M}.json",
            Body=json.dumps(raw),
        )
    return {"checked": len(posts)}
```

The Upload-Post analytics path comes from its API docs, so check the response on your first run and adjust `first_number` if views sit under another name.

### Learn your taste with AgentCore Memory (about 3 hours)

- [ ] Run this once and copy the memory ID:

```python
# scripts/create_memory.py
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")
memory = client.create_memory_and_wait(
    name="ClipPreferences",
    strategies=[{"userPreferenceMemoryStrategy": {
        "name": "ClipTaste",
        "namespaces": ["/preferences/{actorId}"],
    }}],
)
print("MEMORY_ID =", memory["id"])
```

- [ ] Replace `services/notify/webhook.py`. Every decision now becomes a memory event, which AgentCore distils into preferences, and a `/views` command logs counts for TikTok posts you finished by hand:

```python
# services/notify/webhook.py
import datetime
import json
import os

import boto3

from app import cfg, telegram

sfn = boto3.client("stepfunctions")
agentcore = boto3.client("bedrock-agentcore")
table = boto3.resource("dynamodb").Table(os.environ["TABLE"])


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if headers.get("x-telegram-bot-api-secret-token") != cfg()["webhook_secret"]:
        return {"statusCode": 403, "body": "forbidden"}  # not from Telegram
    update = json.loads(event.get("body") or "{}")
    message = update.get("message") or {}
    if str(message.get("chat", {}).get("id")) == str(cfg()["chat_id"]) and message.get("text", "").startswith("/views"):
        return log_views(message["text"])
    query = update.get("callback_query")
    if not query or str(query["from"]["id"]) != str(cfg()["chat_id"]):
        return {"statusCode": 200, "body": "ignored"}  # only you can approve

    action, reason, clip_id = query["data"].split("|", 2)
    approved = action == "a"
    try:
        item = table.update_item(
            Key={"pk": f"CLIP#{clip_id}", "sk": "META"},
            UpdateExpression="SET #s = :s, #r = :r",
            ConditionExpression="#s = :pending",  # a second tap can't decide twice
            ExpressionAttributeNames={"#s": "status", "#r": "reason"},
            ExpressionAttributeValues={
                ":s": "APPROVED" if approved else "REJECTED", ":r": reason, ":pending": "PENDING",
            },
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        note = "Already decided"
    else:
        sfn.send_task_success(
            taskToken=item["token"], output=json.dumps({"approved": approved, "reason": reason})
        )
        note = "Approved" if approved else f"Rejected ({reason})"
        remember(clip_id, json.loads(item["candidate"]), note)
    telegram("answerCallbackQuery", {"callback_query_id": query["id"], "text": note})
    return {"statusCode": 200, "body": "ok"}


def remember(clip_id, c, note):
    """Every decision becomes a memory event; AgentCore distils them into your preferences."""
    agentcore.create_event(
        memoryId=os.environ["MEMORY_ID"],
        actorId="rehan",
        sessionId=clip_id,
        eventTimestamp=datetime.datetime.now(datetime.timezone.utc),
        payload=[{"conversational": {"role": "USER", "content": {"text": (
            f"{note}: a {c['end'] - c['start']:.0f}-second clip titled '{c['title']}' "
            f"with the hook '{c['hook']}'."
        )}}}],
    )


def log_views(text):
    """/views <clip_id> <platform> <age_days> <views>, for TikTok drafts you posted by hand."""
    _, clip_id, platform, age, views = text.split()
    table.put_item(Item={
        "pk": f"CLIP#{clip_id}", "sk": f"METRIC#{platform}#d{int(age)}", "views": int(views),
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    telegram("sendMessage", {"chat_id": cfg()["chat_id"], "text": f"Logged {views} views"})
    return {"statusCode": 200, "body": "ok"}
```

- [ ] Give the Moment Finder your preferences. Add a memory client and this function, and append the result to the prompt:

```python
memory = boto3.client("bedrock-agentcore", region_name=REGION)


def preferences(memory_id):
    """What AgentCore Memory has learned from your approvals and rejections."""
    res = memory.retrieve_memory_records(
        memoryId=memory_id,
        namespace="/preferences/rehan",
        searchCriteria={"searchQuery": "which clips does Rehan approve or reject, and why", "topK": 8},
    )
    return "\n".join(r["content"]["text"] for r in res["memoryRecordSummaries"]) or "None yet"

# In invoke(), the prompt becomes:
        f"Find clip candidates in this video. Campaign rules (JSON): {payload['campaign_rules']}\n"
        f"Rehan's preferences so far:\n{preferences(payload['memory_id'])}",
```

### Performance library and weekly report (about 4 hours)

- [ ] Add a second data source to the `clip-transcripts` knowledge base: S3 prefix `kb/performance/`, no chunking. Copy its data source ID.
- [ ] Add an `Analyst` agent with `agentcore add agent`, deploy it, and copy its ARN:

```python
# agents/clipagents/app/Analyst/main.py
import json

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel

app = BedrockAgentCoreApp()

SYSTEM = """You review a clipper's week of posts. Be concrete: cite clips, platforms and numbers.
Compare what performed at the top against the bottom. Suggest at most three changes for next week."""


class Report(BaseModel):
    summary: str
    what_worked: list[str]
    what_to_change: list[str]


@app.entrypoint
def invoke(payload, context):
    agent = Agent(
        model=BedrockModel(model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", region_name="us-east-1"),
        system_prompt=SYSTEM,
    )
    result = agent(json.dumps(payload), structured_output_model=Report)
    return result.structured_output.model_dump()


if __name__ == "__main__":
    app.run()
```

- [ ] Create `services/notify/weekly.py`. It turns settled 7-day results into library documents tagged top, middle or bottom, then sends the Analyst's report:

```python
# services/notify/weekly.py
import datetime
import json
import os
import uuid

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config

from app import cfg, telegram

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
bedrock_agent = boto3.client("bedrock-agent")
agentcore = boto3.client("bedrock-agentcore", config=Config(read_timeout=900, retries={"max_attempts": 1}))
BUCKET = os.environ["BUCKET"]


def bucket_for(views, all_views):
    ranked = sorted(all_views)
    rank = ranked.index(views) / max(len(ranked) - 1, 1)
    return "top" if rank >= 0.75 else "bottom" if rank <= 0.25 else "middle"


def handler(event, context):
    items = table.scan(FilterExpression=Attr("sk").begins_with("METRIC#"))["Items"]
    latest = {}  # (clip, platform) -> the most recent snapshot
    for m in items:
        _, platform, age = m["sk"].split("#")
        key = (m["pk"], platform)
        if key not in latest or int(age[1:]) > latest[key]["age"]:
            latest[key] = {"age": int(age[1:]), "views": int(m["views"])}

    week_views = [v["views"] for v in latest.values()]
    written = 0
    for (clip_pk, platform), stats in latest.items():
        if stats["age"] < 7:
            continue  # only settled numbers go into the library
        clip = table.get_item(Key={"pk": clip_pk, "sk": "META"}).get("Item", {})
        cand = json.loads(clip.get("candidate", "{}"))
        doc_key = f"kb/performance/{clip_pk[5:]}-{platform}.txt"
        s3.put_object(Bucket=BUCKET, Key=doc_key, Body=(
            f"Platform: {platform}. Views after {stats['age']} days: {stats['views']}.\n"
            f"Title: {cand.get('title')}\nHook: {cand.get('hook')}\n"
            f"Length: {cand.get('end', 0) - cand.get('start', 0):.0f}s\nWhy it was picked: {cand.get('rationale')}"
        ))
        meta = {"metadataAttributes": {"kind": "performance", "platform": platform,
                                       "result": bucket_for(stats["views"], week_views)}}
        s3.put_object(Bucket=BUCKET, Key=doc_key + ".metadata.json", Body=json.dumps(meta))
        written += 1
    if written:
        bedrock_agent.start_ingestion_job(
            knowledgeBaseId=os.environ["TRANSCRIPT_KB_ID"], dataSourceId=os.environ["PERFORMANCE_DS_ID"]
        )

    summary = [{"clip": k[0][5:], "platform": k[1], **v} for k, v in latest.items()]
    resp = agentcore.invoke_agent_runtime(
        agentRuntimeArn=os.environ["ANALYST_ARN"],
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps({"week_ending": datetime.date.today().isoformat(), "posts": summary}).encode(),
    )
    report = json.loads(resp["response"].read())
    text = (f"Week ending {datetime.date.today():%d %b}\n\n{report['summary']}\n\nWorked:\n- "
            + "\n- ".join(report["what_worked"]) + "\n\nChange next week:\n- " + "\n- ".join(report["what_to_change"]))
    telegram("sendMessage", {"chat_id": cfg()["chat_id"], "text": text})
    return {"library_docs": written}
```

### Video index with Marengo (about 4 hours)

- [ ] Create a second knowledge base in the console: data source `s3://YOUR_MEDIA_BUCKET/kb/video/`, embeddings model TwelveLabs Marengo Embed 3.0, vector store S3 Vectors with Quick create. Copy its ID and data source ID.
- [ ] Stop and skip this part if S3 Vectors isn't offered for Marengo. The OpenSearch Serverless alternative costs about $175 a month even when idle.
- [ ] In `prepare_transcript`, ask for a clip `potential` score from 0 to 10 in each chapter's JSON.
- [ ] Add `services/render_preview/index.py` (it reuses the FFmpeg image) and add `index.py` to the Dockerfile's last `COPY` line. Only the most promising 30% of chapters get indexed, at $0.0007 per second of video:

```python
# services/render_preview/index.py
import json
import os
import subprocess
import time

import boto3

s3 = boto3.client("s3")
bedrock_agent = boto3.client("bedrock-agent")


def handler(event, context):
    """Cost cascade: only the most promising 30% of chapters go into the video index."""
    bucket, key, video_id = event["bucket"], event["key"], event["video_id"]
    chapters = json.loads(
        s3.get_object(Bucket=bucket, Key=f"transcripts/{video_id}/chapters.json")["Body"].read()
    )["chapters"]
    ranked = sorted(chapters, key=lambda c: c.get("potential", 0), reverse=True)
    keep = ranked[: max(1, round(len(ranked) * 0.3))]

    src = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
    for i, ch in enumerate(keep):
        out = f"/tmp/{video_id}_{i}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ch["start"]), "-i", src, "-t", str(ch["end"] - ch["start"]),
             "-vf", "scale=-2:480", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
             "-c:a", "aac", "-b:a", "64k", out],
            check=True,
        )
        clip_key = f"kb/video/{video_id}/ch{i:02d}.mp4"
        s3.upload_file(out, bucket, clip_key)
        meta = {"metadataAttributes": {"video_id": video_id, "offset": float(ch["start"])}}
        s3.put_object(Bucket=bucket, Key=clip_key + ".metadata.json", Body=json.dumps(meta))

    kb, ds = os.environ["VIDEO_KB_ID"], os.environ["VIDEO_DS_ID"]
    job = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb, dataSourceId=ds)["ingestionJob"]
    while job["status"] not in ("COMPLETE", "FAILED", "STOPPED"):
        time.sleep(15)
        job = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb, dataSourceId=ds, ingestionJobId=job["ingestionJobId"]
        )["ingestionJob"]
    return {"indexed_chapters": len(keep), "status": job["status"]}
```

- [ ] Add two tools to the Moment Finder. `make_tools` gains a `video_kb_id` parameter, and the video search turns each chunk's timing back into times in the full video ([AWS](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-multimodal-test-and-query.html)):

```python
def make_tools(bucket, kb_id, video_kb_id, video_id):
    # ...the three existing tools stay as they are...

    @tool
    def search_video(query: str) -> str:
        """Search what happens on screen and in the audio: laughter, reactions, visual moments.
        Returns absolute timestamps in the source video."""
        res = kb.retrieve(
            knowledgeBaseId=video_kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {
                "numberOfResults": 6,
                "filter": {"equals": {"key": "video_id", "value": video_id}},
            }},
        )
        hits = []
        for r in res["retrievalResults"]:
            meta = r["metadata"]
            offset = float(meta.get("offset", 0))  # where this chapter starts in the full video
            start = offset + float(meta["x-amz-bedrock-kb-chunk-start-time-in-millis"]) / 1000
            end = offset + float(meta["x-amz-bedrock-kb-chunk-end-time-in-millis"]) / 1000
            hits.append(f"{start:.1f}s-{end:.1f}s (score {r.get('score', 0):.2f})")
        return "\n".join(hits) or "No matches"

    @tool
    def search_past_clips(query: str) -> str:
        """Find your past clips and how they performed (top, middle or bottom). Use them as examples."""
        res = kb.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {
                "numberOfResults": 5,
                "filter": {"equals": {"key": "kind", "value": "performance"}},
            }},
        )
        return "\n---\n".join(r["content"]["text"] for r in res["retrievalResults"]) or "No history yet"

    return [get_chapters, search_transcript, read_transcript, search_video, search_past_clips]

# In invoke(): tools=make_tools(payload["bucket"], payload["kb_id"], payload["video_kb_id"], payload["video_id"])
```

- [ ] In `find_moments/app.py`, add `"video_kb_id": os.environ["VIDEO_KB_ID"]` and `"memory_id": os.environ["MEMORY_ID"]` to the payload.

### CDK changes (about 2 hours)

```python
# New constants
VIDEO_KB_ID = "..."
VIDEO_DS_ID = "..."
PERFORMANCE_DS_ID = "..."  # second data source on the transcript knowledge base
MEMORY_ID = "..."
ANALYST_ARN = "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/Analyst-abc123"

# find_fn environment gains VIDEO_KB_ID and MEMORY_ID. The MomentFinderDataAccess policy gains
# bedrock:Retrieve on the video knowledge base and bedrock-agentcore:RetrieveMemoryRecords on the memory.

        memory_arn = f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:memory/{MEMORY_ID}"
        webhook_fn.add_environment("MEMORY_ID", MEMORY_ID)
        webhook_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:CreateEvent"], resources=[memory_arn],
        ))

        index_fn = lambda_.DockerImageFunction(
            self, "IndexVideoFn",
            code=lambda_.DockerImageCode.from_image_asset(
                "../services/render_preview", platform=PLATFORM, cmd=["index.handler"]
            ),
            architecture=ARCH,
            memory_size=3008,
            timeout=Duration.minutes(15),
            environment={"VIDEO_KB_ID": VIDEO_KB_ID, "VIDEO_DS_ID": VIDEO_DS_ID},
        )
        media.grant_read_write(index_fn)
        index_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{VIDEO_KB_ID}"],
        ))

        metrics_fn = lambda_.Function(
            self, "MetricsFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="app.handler",
            code=lambda_.Code.from_asset("../services/metrics"),
            timeout=Duration.minutes(5),
            environment={"TABLE": table.table_name, "BUCKET": media.bucket_name},
        )
        table.grant_read_write_data(metrics_fn)
        media.grant_put(metrics_fn, "evidence/*")
        sm.Secret.from_secret_name_v2(self, "MetricsKeys", "clip/metrics").grant_read(metrics_fn)

        weekly_fn = lambda_.Function(
            self, "WeeklyFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=ARCH,
            handler="weekly.handler",
            code=lambda_.Code.from_asset("../services/notify"),
            timeout=Duration.minutes(15),
            environment={**telegram_env, "TRANSCRIPT_KB_ID": TRANSCRIPT_KB_ID,
                         "PERFORMANCE_DS_ID": PERFORMANCE_DS_ID, "ANALYST_ARN": ANALYST_ARN},
        )
        table.grant_read_data(weekly_fn)
        media.grant_put(weekly_fn, "kb/performance/*")
        telegram.grant_read(weekly_fn)
        weekly_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:StartIngestionJob"],
            resources=[f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/{TRANSCRIPT_KB_ID}"],
        ))
        weekly_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeAgentRuntime"], resources=[ANALYST_ARN, f"{ANALYST_ARN}/*"],
        ))

        # Daily at 22:00 UTC (8 or 9 am Melbourne); weekly on Sunday 05:00 UTC, before your check-in
        events.Rule(self, "DailyMetrics", schedule=events.Schedule.cron(minute="0", hour="22"),
                    targets=[targets.LambdaFunction(metrics_fn)])
        events.Rule(self, "WeeklyReport", schedule=events.Schedule.cron(minute="0", hour="5", week_day="SUN"),
                    targets=[targets.LambdaFunction(weekly_fn)])

# A new step between PrepareTranscript and FindMoments
        index_video = tasks.LambdaInvoke(
            self, "IndexVideo",
            lambda_function=index_fn,
            payload=sfn.TaskInput.from_object({
                "bucket": sfn.JsonPath.string_at("$.detail.bucket.name"),
                "key": sfn.JsonPath.string_at("$.detail.object.key"),
                "video_id": video_id,
            }),
            result_path=sfn.JsonPath.DISCARD,
        )
        index_video.add_retry(errors=["ConflictException"], interval=Duration.seconds(60), max_attempts=5)

# The COMPLETED branch becomes prepare.next(index_video).next(find).next(each_candidate)
```

### Test it

- [ ] Run the metrics function from the Lambda console (Test tab), then check for `METRIC#` items and files under `evidence/`.
- [ ] Reject three clips with reasons. A few minutes later, run a video and check the Moment Finder's logs (`agentcore logs`) for your preferences in the prompt.
- [ ] Run the weekly function by hand and read the report on Telegram.
- [ ] Ask the Moment Finder for a visual moment, such as "the audience laughing", and check its timestamps against the video.

**Done when:** daily snapshots and evidence land in S3, the weekly report arrives, and your rejection reasons appear as preferences in the Moment Finder's prompt.

**Escape hatch:** if the video index or memory setup stalls, skip it. Drop `search_video` or the preferences line from the Moment Finder, along with the matching payload fields. It still works on transcripts alone, and view tracking matters most.
