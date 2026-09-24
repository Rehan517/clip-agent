# services/notify/app.py
import json
import os
import urllib.request

import boto3

s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")
_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        raw = secrets.get_secret_value(SecretId=os.environ["SECRET_ID"])["SecretString"]
        _cfg = json.loads(raw)
    return _cfg


def telegram(method, payload):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{cfg()['token']}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def handler(event, context):
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": os.environ["BUCKET"], "Key": event["preview_key"]},
        ExpiresIn=3600,
    )
    telegram("sendVideo", {
        "chat_id": cfg()["chat_id"],
        "video": url,
        "caption": event.get("text", ""),
        "supports_streaming": True,
    })
    return {"ok": True}