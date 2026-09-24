---
paths:
  - "services/**"
---

# Lambda rules

- Handlers take `(event, context)` and return JSON-serialisable dicts. Step Functions reads the result from `$.Payload`.
- Create boto3 clients at module level so warm starts reuse them. Calls to AgentCore agents need `Config(read_timeout=900)`.
- Configuration comes from environment variables set in CDK. Secrets come from Secrets Manager and are cached per container.
- Zip-deployed functions use only the standard library and boto3. Anything needing FFmpeg or OpenCV belongs in a container image.
- Step Functions retries failed Lambdas, so make handlers safe to run twice: check state before posting, charging or writing.
- Log one clear line per decision with `print` (it lands in CloudWatch). Never log secrets, API keys or full task tokens.
- When you change a pure function (transcript windows, captions, compliance rule checks), add or update its pytest test.
