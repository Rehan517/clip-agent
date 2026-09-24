# Working with Claude Code on this project

Claude Code types and explains. You make the decisions, do the console work and deploys, and write the parts worth learning. This file covers the one-time setup, how to run a session, and which parts to write yourself.

## One-time setup (about 1 hour)

The same steps are ticked off under "Set up Claude Code" in week 1 of the build guide.

1. **Editor.** Use VS Code with Anthropic's Claude Code extension. Visual Studio only has unofficial community ports.
   - On Windows, install WSL 2 (Ubuntu) and VS Code's WSL extension. Keep the repo inside Ubuntu at `~/clip-agent`, not under `/mnt/c`, which is slow, and open it with `code .` from Ubuntu. Python, Docker, the AWS CLI and Claude Code then all run in Linux, matching the guide.
   - When VS Code offers the recommended extensions from `.vscode/extensions.json`, install them.
2. **Claude Code CLI.** Install it inside WSL, macOS or Linux with `curl -fsSL https://claude.ai/install.sh | bash`, run `claude doctor` to check it, and sign in with your Claude plan. The extension works without the CLI, but `claude mcp` and `claude doctor` need it.
3. **Start conversations in plan mode.** Open VS Code settings, search for "Claude Code: Initial Permission Mode", and choose `plan`. The extension ignores project settings for this, and on Pro and Max plans conversations otherwise start in Auto mode, which acts without asking.
4. **Read-only AWS profile for Claude.**
   - IAM Identity Center, Permission sets, Create permission set, Predefined permission set, `ReadOnlyAccess`, keeping its default name `ReadOnlyAccess`.
   - AWS accounts, select your account, Assign users or groups, pick your user and the `ReadOnlyAccess` permission set.
   - In the terminal, run `aws configure sso --profile clip-readonly`. The `--profile` flag matters: your terminal already uses `AWS_PROFILE=clip`, so without it the wizard would overwrite that profile. Type `clip` for the session name, press Enter to keep the saved start URL, region and scopes, and pick the ReadOnlyAccess role.
   - Test it: `aws sts get-caller-identity --profile clip-readonly` shows `AWSReservedSSO_ReadOnlyAccess`, and `aws s3 mb s3://clip-test-$RANDOM --profile clip-readonly` fails with AccessDenied.
   - `ReadOnlyAccess` lets Claude read logs, Step Functions history, DynamoDB items and S3 objects, but not secret values, and nothing it can do changes your account.
5. **Unzip this kit into the repo root and commit it.** From `~/clip-agent`, run `unzip -o` with the zip's path: `/mnt/c/Users/YOUR_WINDOWS_USER/Downloads/clip-agent-kit-v2.zip` on Windows, `~/Downloads/clip-agent-kit-v2.zip` on a Mac.
6. **Check it worked** in a new conversation:
   - `/mcp` lists `aws-knowledge` as connected.
   - `/output-style` shows Learning.
   - `/permissions` shows the deny rules.
   - Typing `/` shows `/step`, `/console`, `/explain`, `/diagnose`, `/review-mine`, `/quiz` and `/wrap`.
   - Asking "What are you not allowed to do in this repo?" gets an answer that matches `CLAUDE.md`.

## A build session (about 3 hours)

1. Open the living build guide and pick the next unticked step.
2. Start a new conversation for each step. Short conversations stay focused and use less of your plan.
3. Run `/step 2 Build the FFmpeg Lambda`. Claude reads that week's guide, explains the concepts and proposes a plan while in plan mode. Ask questions until the plan makes sense, then approve it and choose **Manual**, so every edit shows as a diff you accept or reject.
4. When Claude leaves a `TODO(human)` comment, write that part yourself, then tell Claude you're done. That's the Learning output style at work.
5. For console work, run `/console create the Telegram secret in Secrets Manager` and follow the steps yourself.
6. Deploy and test in your own terminal (`cdk deploy ClipPipeline`, uploads, curl). Watch the CloudFormation events and the Step Functions graph in the console; that's where you see what your code built.
7. When something breaks, run `/diagnose` with the error pasted in. The 90-minute rule still applies.
8. Before committing, run `/explain` and make sure you could explain every changed line yourself. Then commit.
9. In the last 15 minutes, run `/quiz`, then `/wrap`, and tick the boxes in the living guide.

## Write these parts yourself

Let Claude write the glue, but write these yourself and then run `/review-mine` on them. They're the parts interviewers ask about.

| Week | Write it yourself | Why it's worth it |
| --- | --- | --- |
| 2 | The Transcribe polling loop (Wait, Get, Choice) in `pipeline_stack.py` | Step Functions basics and thinking about retries |
| 3 | `windows()` in `prepare_transcript` and the Moment Finder's Pydantic schema and prompt | Chunking for RAG and designing structured output |
| 4 | The webhook's three checks: secret header, chat ID, conditional write | Webhook security and idempotency |
| 5 | `rule_checks()` in the Compliance agent and the daily cap in `publish.py` | Deterministic guardrails next to LLM judgement |
| 6 | The metrics loop and the evidence writes | Observability, and evidence for payout disputes |
| 7 | The Cedar policy, the OIDC trust conditions and the IAM simulator test | Security engineering you can talk through |
| 8 | `recall_at_k` and `docs/results.md` | Measuring AI output instead of trusting it |

## Console and CDK: learn in one, keep in the other

- **Created by hand in the console, as the guide says:** Identity Center, budgets, Bedrock model access, knowledge bases, the guardrail, secrets, the Telegram bot and Upload-Post.
- **Managed by CDK:** S3, DynamoDB, Lambda, Step Functions, API Gateway, EventBridge and IAM roles. For each new service, first build a throwaway version in the console (a hello-world Lambda, a three-state workflow in Step Functions Workflow Studio), delete it, then write the CDK. After `cdk deploy`, inspect what CDK built, especially the IAM policies its `grant_*` calls generated.
- **Never edit a CDK-managed resource in the console.** The next deploy silently overwrites it, which is called drift.
- **Console-to-Code** records what you click and generates CDK Python for Lambda, Step Functions, S3, DynamoDB, EventBridge, API Gateway, Secrets Manager and more, with a monthly cap on free CDK generations. Record a throwaway build, then ask Claude to compare the output with the guide's CDK.

## What Claude can and can't do here

- The real boundary is IAM. Claude's shell uses `clip-readonly`, so even a wrong command can't change your account.
- The deny rules in `.claude/settings.json` (deploys, `--profile clip`, `git push`, reading `.env` and `~/.aws`) are a second layer. Claude Code's docs say Bash rules match the command text and aren't a security boundary on their own, which is why the read-only profile matters.
- You deploy, you push, and you create console resources.

## Staying efficient

- Keep one step per conversation. If a debugging session runs long, use `/compact`.
- The Learning style writes longer answers and hands you small pieces to write. If you fall behind the plan, switch to `/output-style Explanatory` for glue code, then back to Learning for the table above.
- `/usage` shows how close you are to your plan's limits.
- Use your Claude subscription for Claude Code rather than pointing it at Bedrock. Your AWS credits are for the project itself.
- When you correct Claude the same way twice, add a line to `CLAUDE.md`.

## Files in this kit

| File | What it does |
| --- | --- |
| `CLAUDE.md` | Project context, how to work with you, AWS rules. Loaded at the start of every conversation |
| `.claude/settings.json` | Learning output style, plan mode for terminal sessions, the read-only AWS profile, allow and deny rules |
| `.claude/rules/` | Extra rules that load only when Claude works in `infra/`, `services/` or `agents/` |
| `.claude/skills/` | `/step`, `/console`, `/explain`, `/diagnose`, `/review-mine`, `/quiz`, `/wrap` |
| `.mcp.json` | The AWS Knowledge MCP server: current AWS, CDK and Strands docs, with no key needed |
| `.vscode/extensions.json` | Recommended VS Code extensions |
| `docs/guide/` | The build guide, split by week so Claude reads only what it needs |
| `docs/architecture.md` | The architecture doc, for the reasons behind the design |
| `docs/learning-log.md` | Your running notes, filled in by `/quiz` and `/wrap` |

The guide and architecture copies were exported on 24 September 2026. If the living docs change a lot, export them again.
