---
description: Debug an AWS or pipeline error with me, gathering evidence first and teaching the method.
argument-hint: "<error message or what went wrong>"
disable-model-invocation: true
---

Something's broken: $ARGUMENTS

Teach me to debug it rather than just fixing it.

1. Name the component that most likely failed, and why, in one or two lines.
2. Gather evidence with read-only commands only: CloudWatch logs, Step Functions execution history, DynamoDB items, `cdk diff`. Show each command and what it told us.
3. State the most likely cause, and check it against `docs/guide/troubleshooting.md`.
4. Propose the smallest fix and explain why it works. If the fix needs the console or a deploy, give me the steps and don't do it yourself.
5. End with one sentence on how I'd spot this faster next time.
