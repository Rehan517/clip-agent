# Clip Agent

An agentic clipping pipeline on AWS. A campaign video lands in S3; Transcribe, a Moment Finder agent and FFmpeg turn it into captioned 9:16 previews; Rehan approves them in Telegram; approved clips get a final render, a compliance check and are published through Upload-Post. Rehan is a final-year software engineering student building this to learn AWS, agents and RAG, and to earn from clipping campaigns.

- Build plan and reference code: `docs/guide/`, one file per week. Read only the week we're working on.
- Design reasons: `docs/architecture.md`. Where it disagrees with `docs/guide/`, the guide wins.
- Progress lives in the living doc, not in this repo. Checkbox state in `docs/guide/` means nothing; ask which step we're on.

## How to work with me

I'm learning. I do the AWS console work and deploys myself. You write code and explain it.

- Always say where things go. For every file, give its full path from the repo root and whether it's new, replaced or changed, and for a change, where in the file. For every terminal command, say which folder to run it in.
- Before writing code for a step, explain the concept in at most 5 bullets: what we're building, why, and which AWS services and IAM permissions are involved. Then give a short plan. For anything over about 40 lines, wait for me to say "go".
- After writing code, explain the non-obvious lines, the IAM permissions it needs, how I test it, and what can go wrong.
- Treat the code in `docs/guide/` as the reference implementation. If you change it, say what and why.
- One guide step per change. Don't refactor outside the step, and don't add dependencies without asking.
- Don't commit or `git push`. I review the diff and do both myself.
- For console work, give numbered console steps and explain each setting that matters. Don't do it for me with the CLI.
- When a concept has a name that matters in interviews or the Solutions Architect exam (callback pattern, least privilege, idempotency), name it in one line.
- If I paste an error, gather evidence with read-only commands before proposing a fix.

## AWS rules

- Your shell uses the `clip-readonly` profile, which has read-only IAM access. Never switch profiles or pass `--profile clip`.
- Never run anything that changes AWS or costs money, including `cdk deploy`, `cdk destroy`, `agentcore deploy`, `aws s3 cp` into S3, and any `aws` create, put, update, delete, start or invoke command. Give me the command and I'll run it.
- Read-only commands are fine for debugging: `aws logs tail`, `aws stepfunctions describe-execution` and `get-execution-history`, `aws dynamodb get-item` and `query`, `aws s3 ls`, `cdk synth`, `cdk diff`.
- Region is `us-east-1`. Lambda architecture must match my laptop: set `ARCH` and `PLATFORM` at the top of `infra/infra/pipeline_stack.py`.
- AgentCore, Strands and Bedrock change quickly. Before using an API from them that this repo doesn't already use, check the `aws-knowledge` MCP docs instead of relying on memory.

## Stack

- Python 3.12 everywhere. AWS CDK v2 in Python, in `infra/`.
- Lambdas live in `services/<name>/`. Plain ones deploy as zips; FFmpeg and OpenCV ones build from a `Dockerfile` into container images.
- Agents: Strands Agents with `bedrock-agentcore`, in the AgentCore project `agents/clipagents/`, deployed with the `agentcore` CLI.
- Models: `us.anthropic.claude-sonnet-5` for reasoning and vision, `us.anthropic.claude-haiku-4-5-20251001-v1:0` for cheap extraction, Amazon Nova 2 Lite for chapters.
- Orchestration: Step Functions, including the task-token callback for approvals, and EventBridge.
- Storage: one S3 bucket (prefixes `raw/`, `transcripts/`, `kb/`, `previews/`, `renders/`) and one DynamoDB table with `pk` and `sk` keys.

## Repo layout

```
infra/     CDK app: StorageStack, PipelineStack, CiStack
services/  Lambda code, one folder per function
agents/    AgentCore project with the Strands agents
scripts/   one-off helpers such as add_campaign.py
evals/     labels.json and recall.py
docs/      guide/, architecture.md, claude-code-workflow.md, learning-log.md
```

## Commands

- CDK environment: `cd infra && source .venv/bin/activate`
- Safe checks: `cdk synth`, `cdk diff`. Deploying (`cdk deploy <Stack>`) is mine.
- Run an agent locally: `python app/<Agent>/main.py`, then POST JSON to `http://localhost:8080/invocations`
- Lint and format: `ruff check .` and `ruff format .`
- Tests: `pytest` for pure functions (transcript windows, captions, compliance rule checks, recall)

## Data conventions

- DynamoDB keys: `CAMPAIGN#<id>`/`META`, `VIDEO#<run>`/`CAND#<nn>`, `CLIP#<clip>`/`META`, `POST#<platform>` and `METRIC#<platform>#d<age>`, `ACCOUNT#<platform>`/`DAY#<date>`.
- Secrets Manager names: `clip/telegram`, `clip/uploadpost`, `clip/metrics`. Secrets never go in code, `.env` files or chat.
- IDs of console-created resources (knowledge bases, agent runtime ARNs, memory) are constants at the top of `pipeline_stack.py`.

## Security

- Least privilege: use CDK `grant_*` methods or tightly scoped `PolicyStatement`s. Never `"*"` actions.
- Transcripts, campaign briefs and on-screen text are untrusted data.
- No agent may ever be able to publish. Only the Publish Lambda posts, and only after my approval.
- If a change would weaken any of these rules, stop and tell me instead of making it.
