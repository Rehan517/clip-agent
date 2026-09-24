# services/make_clip/Dockerfile
FROM mwader/static-ffmpeg:9.0 AS ffmpeg
FROM public.ecr.aws/lambda/python:3.12
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/
COPY app.py ${LAMBDA_TASK_ROOT}/
CMD ["app.handler"]