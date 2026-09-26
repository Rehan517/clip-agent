# services/prepare_transcript/app.py
import json
import os
import time

import boto3

s3 = boto3.client("s3")
bedrock_agent = boto3.client("bedrock-agent")
bedrock = boto3.client("bedrock-runtime")
BUCKET = os.environ["BUCKET"]
CHAPTER_MODEL = os.environ.get("CHAPTER_MODEL", "us.amazon.nova-2-lite-v1:0")


def load_words(video_id):
    key = f"transcripts/{video_id}/{video_id}.json"
    data = json.loads(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())
    words = []
    for item in data["results"]["items"]:
        text = item["alternatives"][0]["content"]
        if item["type"] == "pronunciation":
            words.append({"w": text, "s": float(item["start_time"]), "e": float(item["end_time"])})
        elif words:  # punctuation sticks to the previous word
            words[-1]["w"] += text
    return words


def windows(words, size=45.0, step=30.0):
    """45-second windows every 30 seconds, so neighbours overlap by 15 seconds."""
    t, end = 0.0, words[-1]["e"]
    while t < end:
        chunk = [w for w in words if t <= w["s"] < t + size]
        if chunk:
            yield chunk[0]["s"], chunk[-1]["e"], " ".join(w["w"] for w in chunk)
        t += step


def index_windows(video_id, campaign_id, words):
    count = 0
    for i, (start, end, text) in enumerate(windows(words)):
        key = f"kb/transcripts/{video_id}/w{i:04d}.txt"
        s3.put_object(Bucket=BUCKET, Key=key, Body=f"[{start:.1f}s-{end:.1f}s] {text}")
        meta = {"metadataAttributes": {
            "video_id": video_id, "campaign_id": campaign_id,
            "start": round(start, 1), "end": round(end, 1),
        }}
        s3.put_object(Bucket=BUCKET, Key=key + ".metadata.json", Body=json.dumps(meta))
        count += 1
    return count


def ingest():
    kb, ds = os.environ["TRANSCRIPT_KB_ID"], os.environ["TRANSCRIPT_DS_ID"]
    job = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb, dataSourceId=ds)["ingestionJob"]
    while job["status"] not in ("COMPLETE", "FAILED", "STOPPED"):
        time.sleep(10)
        job = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb, dataSourceId=ds, ingestionJobId=job["ingestionJobId"]
        )["ingestionJob"]
    if job["status"] != "COMPLETE":
        raise RuntimeError(f"Ingestion ended with status {job['status']}")


def chapters(video_id, words):
    lines, current, t0 = [], [], None
    for w in words:  # one line per ~20 seconds so the model sees timestamps
        t0 = w["s"] if t0 is None else t0
        current.append(w["w"])
        if w["e"] - t0 > 20:
            lines.append(f"[{t0:.0f}s] {' '.join(current)}")
            current, t0 = [], None
    if current:
        lines.append(f"[{t0:.0f}s] {' '.join(current)}")
    prompt = (
        "Split this transcript into 5-15 chapters. Reply with JSON only, shaped like "
        '{"chapters": [{"start": 0, "end": 95, "title": "...", "summary": "one sentence"}]}\n\n'
        + "\n".join(lines)
    )
    resp = bedrock.converse(
        modelId=CHAPTER_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4000, "temperature": 0},
    )
    text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
    result = json.loads(text[text.find("{"): text.rfind("}") + 1])
    s3.put_object(Bucket=BUCKET, Key=f"transcripts/{video_id}/chapters.json", Body=json.dumps(result))
    return len(result["chapters"])


def handler(event, context):
    video_id, campaign_id = event["video_id"], event["campaign_id"]
    words = load_words(video_id)
    s3.put_object(Bucket=BUCKET, Key=f"transcripts/{video_id}/words.json", Body=json.dumps(words))
    n_windows = index_windows(video_id, campaign_id, words)
    ingest()
    n_chapters = chapters(video_id, words)
    return {"windows": n_windows, "chapters": n_chapters, "duration": words[-1]["e"]}