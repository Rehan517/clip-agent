# services/make_clip/app.py
import subprocess

import boto3

s3 = boto3.client("s3")


def handler(event, context):
    bucket, key, video_id = event["bucket"], event["key"], event["video_id"]
    start = float(event.get("start", 60))
    end = float(event.get("end", start + 30))
    # FFmpeg reads straight from S3 over HTTPS, so the full video never downloads
    src = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
    )
    out = f"/tmp/{video_id}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", src, "-t", f"{end - start:.2f}",
            "-vf", "crop=ih*9/16:ih,scale=540:960",  # centre crop to 9:16
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out,
        ],
        check=True,
    )
    preview_key = f"previews/{video_id}/rough.mp4"
    s3.upload_file(out, bucket, preview_key, ExtraArgs={"ContentType": "video/mp4"})  # Telegram checks the file type
    return {"preview_key": preview_key}