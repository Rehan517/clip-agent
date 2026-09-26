"""Usage: python scripts/add_campaign.py whop-acme-podcast brief.txt"""
import json
import sys
import uuid

import boto3

ANALYST_ARN = "arn:aws:bedrock-agentcore:us-east-1:730763715981:runtime/clipagents_CampaignAnalyst-TVz3nm82sP"  # agentcore status
TABLE = "ClipStorage-State1C20CC9A-M0L8TRVHUDP9"  # your table name from the DynamoDB console

campaign_id, brief_path = sys.argv[1], sys.argv[2]
resp = boto3.client("bedrock-agentcore", region_name="us-east-1").invoke_agent_runtime(
    agentRuntimeArn=ANALYST_ARN,
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"brief": open(brief_path).read()}).encode(),
)
raw = resp["response"].read().decode()
print("RAW RESPONSE:", repr(raw[:1000]))
spec = json.loads(raw)
boto3.resource("dynamodb", region_name="us-east-1").Table(TABLE).put_item(
    Item={"pk": f"CAMPAIGN#{campaign_id}", "sk": "META", "spec": json.dumps(spec)}
)
print(json.dumps(spec, indent=2))
print(f"Upload videos to s3://clipstorage-mediaa721a567-2nsgbirlddwb/raw/{campaign_id}/")