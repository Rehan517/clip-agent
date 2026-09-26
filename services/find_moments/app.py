# services/find_moments/app.py
import json
import os
import uuid

import boto3
from botocore.config import Config

# Agent runs can take a few minutes, longer than boto3's default 60-second read timeout
agentcore = boto3.client("bedrock-agentcore", config=Config(read_timeout=900, retries={"max_attempts": 1}))
table = boto3.resource("dynamodb").Table(os.environ["TABLE"])


def handler(event, context):
    video_id, campaign_id = event["video_id"], event["campaign_id"]
    item = table.get_item(Key={"pk": f"CAMPAIGN#{campaign_id}", "sk": "META"}).get("Item", {})
    resp = agentcore.invoke_agent_runtime(
        agentRuntimeArn=os.environ["MOMENT_FINDER_ARN"],
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps({
            "video_id": video_id,
            "campaign_rules": item.get("spec", "{}"),
            "bucket": os.environ["BUCKET"],
            "kb_id": os.environ["TRANSCRIPT_KB_ID"],
        }).encode(),
    )
    body = json.loads(resp["response"].read())
    candidates = sorted(body["candidates"], key=lambda c: c["score"], reverse=True)
    for i, c in enumerate(candidates):
        table.put_item(Item={"pk": f"VIDEO#{video_id}", "sk": f"CAND#{i:02d}", "data": json.dumps(c)})
    return {"candidates": candidates}