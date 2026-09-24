> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

# Build guide overview

## How this guide gets you to the finish line

The finish line is the MVP at the end of week 5. Weeks 6–8 improve a system that already works, so a slow week late in the plan never leaves you with half a project.

**MVP, end of week 5:**

1. You drop a campaign's source video into S3.
2. Within 20 minutes, 8 or more preview clips arrive on your phone through a Telegram bot.
3. The clips you approve render with captions and post to YouTube Shorts and TikTok with the campaign's required tags.
4. Your phone pings you with the links to submit to the campaign.

### Rules that stop projects dying

- **Always have something that runs end to end.** Week 2 builds a crude pipeline from upload to phone. Every later week upgrades one stage of it, so you never spend a week on something you can't demo.
- **Tick the boxes as you go.** Every step is a checkbox. The Sunday check-in reads them, logs your progress at the bottom of this guide, and picks your three priorities for the next week.
- **Demo every Sunday.** Record a 60-second screen capture of what works. Eight of these make your build log, your LinkedIn posts and your interview material.
- **The 90-minute rule.** Stuck on one error for 90 minutes? Take that week's escape hatch or ask for help (see "When you get stuck"). Insisting on the hard way is how side projects die.
- **Park new ideas.** Add them to a "Later" list in your README instead of building them. Stretch ideas wait until after week 8.
- **Earn from week 1.** Manual clipping pays before the code does, which carries your motivation through the AWS learning curve.
- **If something slips, cut scope, not the MVP.** Weeks 6–8 shrink first.

### Weekly rhythm (15+ hours)

| When | What |
| --- | --- |
| Five build sessions of about 3 hours | Each ends with a Git commit and a one-line note of what's next |
| One clipping session | Review clips, post, submit links, check campaign dashboards |
| Sunday | Record the demo, tick boxes; the check-in arrives in the evening |

## The 8-week plan

Week 1 starts Monday 28 September, and the MVP lands at the end of week 5. Everything runs in us-east-1 (N. Virginia), where the video search features are available.

| Week | Due | Build | Done when |
| --- | --- | --- | --- |
| 1 | Oct 4, 2026 | Locked-down AWS account, tools, repo, CDK bootstrap; campaigns joined; clips made by hand | `cdk deploy` works from your laptop and your first manual clips are submitted |
| 2 | Oct 11, 2026 | Walking skeleton: S3 upload, EventBridge, Step Functions, Transcribe, a fixed 30-second clip, Telegram | A video you upload turns into a transcript and a rough clip on your phone |
| 3 | Oct 18, 2026 | Campaign Analyst and Moment Finder on Bedrock, deployed to AgentCore Runtime; transcript knowledge base | The pipeline sends the Moment Finder's picks instead of a fixed clip |
| 4 | Oct 25, 2026 | FFmpeg preview Lambda (9:16 crop, captions); approve and reject buttons using task tokens | Tapping Approve on your phone resumes the Step Functions run |
| 5 | Nov 1, 2026 | Editor agent, full-quality FFmpeg render, Compliance Reviewer, Upload-Post publisher, submit alerts | **MVP:** approved clips post to Shorts and TikTok and you get the links to submit |
| 6 | Nov 8, 2026 | Metrics poller, Performance KB, Marengo video index, AgentCore Memory, weekly report | The Moment Finder and the report both use real view data |
| 7 | Nov 15, 2026 | Your own render worker with face tracking, Guardrails, Gateway with a Cedar policy, GitHub deploys over OIDC | Your renderer handles most clips, and a test proves unapproved posts are blocked |
| 8 | Nov 22, 2026 | Evals, cost-per-clip report, README, demo video, blog post, resume bullets; buffer | Repo public and write-up published |

Semester 2 exams usually fall in November, so check your timetable. If exams land in weeks 6–8, stop after the MVP and resume afterwards, since the MVP is built to be a stable place to pause.

### Simplifications from the architecture doc

- **Approvals happen in a Telegram bot, not a web app.** It's quicker to build and already on your phone. A web dashboard becomes a stretch goal.
- **Rendering runs in Lambda container images, not Fargate.** There's no VPC or cluster to manage, and a Lambda run gets up to 15 minutes, plenty for a 60-second clip.
- **Your own FFmpeg renderer makes the final clips from week 5.** Crayo's API becomes optional: its docs sit behind a login, and the MVP shouldn't depend on an API you can't inspect yet.
- **Campaign rules live in a structured spec, not a knowledge base.** The Campaign Analyst's JSON is exact and easy to check in code.
- **Agents call their tools in-process at first.** AgentCore Gateway and the Cedar policy arrive in week 7.
- **Knowledge bases are created in the console.** Their IDs go into constants at the top of your CDK stack.

## How to follow the steps

Each step says where you do it, what to type or paste, and what you should see when it has worked. Tick the box once you see it.

| Where | What it is | How to open it |
| --- | --- | --- |
| **Terminal** | Where you type commands. On Windows it's the **Ubuntu** app (WSL), not PowerShell; on a Mac it's **Terminal** | Start menu → Ubuntu, or Spotlight → Terminal. VS Code's **Terminal → New Terminal** opens the same thing |
| **VS Code** | Where you create and edit files | `code .` in the terminal, from `~/clip-agent` |
| **Console** | The AWS website | Your access portal, then your account → **AdministratorAccess** |

**The grey boxes**

- **Commands** (boxes marked `bash`) go in the terminal, one line at a time: paste a line, press Enter, and check it didn't print an error before the next. Paste with right-click on Windows or Cmd+V on a Mac. A line ending in `\` carries on to the next line, so paste those lines together.
- **Files** (boxes marked `python`, `dockerfile` and so on) go in VS Code. Their first line names the file as a path from `clip-agent`, like `# infra/infra/storage_stack.py`, and the step says what to do with it:
  - **Create:** in the terminal, from `~/clip-agent`, run `code` and the path, for example `code services/notify/app.py`. Paste the whole box into the empty tab and save with Ctrl+S (Cmd+S). When the step says the folder is new, run the `mkdir -p` line it gives first.
  - **Replace:** open the file the same way, select everything with Ctrl+A (Cmd+A), paste, save.
  - **Change** (weeks 3–7): the box holds only the new lines, and its `#` comments say where each part goes. The easiest way is to ask Claude Code, for example `/step 3 Call the agent from the pipeline`: it puts the lines in place and shows each edit for you to accept.
- **Placeholders** are capitals starting with `YOUR_`, like `YOUR_WINDOWS_USER`. Swap in your own value; the step says where to find it.

**Folders**

The terminal always sits in one folder, and in Ubuntu the prompt shows it: `~/clip-agent/infra$` means your project's `infra` folder. "No such file or directory" usually means you're in the wrong folder, and `ModuleNotFoundError` usually means a new terminal without the Python environment switched on. `pwd` prints where you are, `ls` lists what's there (`ls -a` includes hidden files like `.claude`), `cd ~/clip-agent` goes to the project, and `cd ..` goes up one level. The guide assumes your project is at `~/clip-agent`. If `cd ~/clip-agent` says No such file or directory, you made it somewhere else: go into it, run `pwd`, and use that path wherever the guide says `~/clip-agent`.

```text
clip-agent/                    your project, at ~/clip-agent
├── infra/                     the CDK app: run cdk commands in here
│   ├── app.py                 lists your stacks
│   ├── cdk.json, requirements.txt, .venv/
│   └── infra/                 the stacks' code (yes, infra inside infra)
│       ├── storage_stack.py   week 1: bucket and table
│       └── pipeline_stack.py  week 2 on: Lambdas and Step Functions
├── services/                  one folder per Lambda: make_clip/, notify/, ...
├── agents/                    your agents, from week 3
├── scripts/, evals/           helpers and tests, from week 3
├── samples/                   test videos (Git ignores .mp4 files)
├── docs/                      the kit's copy of this guide
└── CLAUDE.md, .claude/        the Claude Code kit
```

**Every new terminal** starts in your home folder with nothing switched on. Before any `cdk` command:

```bash
cd ~/clip-agent/infra
source .venv/bin/activate
```

`(.venv)` at the start of the prompt means it's on. When an AWS command says your token or session has expired, run `aws sso login --profile clip`.

**When something doesn't match**, stop at that step rather than carrying on. Look it up in [When you get stuck](troubleshooting.md), paste the full error into Claude Code after `/diagnose`, or comment on the step here and tag @Claude.
