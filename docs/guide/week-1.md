> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## Week 1: Lock down AWS, set up tools, clip by hand

By Sunday you can deploy to AWS from your laptop without any stored keys, and your first hand-made clips are submitted to campaigns.

### Secure the account (about 2 hours)

- [ ] Turn on MFA for the root user, then stop using root.
- [ ] Upgrade to the Paid plan (Billing and Cost Management, Account plan). Your credits carry over, and the free plan blocks some AWS Marketplace offers and closes the account when credits run out ([AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)). Claude on Bedrock is billed through AWS Marketplace ([model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5.html)).
- [ ] Create a monthly cost budget of $40 with email alerts, using the console's monthly budget template.
- [ ] Turn on Cost Anomaly Detection with an email alert.
- [ ] Enable IAM Identity Center in us-east-1. Create your user, assign it the AdministratorAccess permission set on your account, and register MFA. Sign in through the access portal from now on.
- [ ] Set the console region to us-east-1 (top right) and leave it there.
- [ ] In Bedrock, open Claude Sonnet 5 in the model catalog and submit Anthropic's one-time use-case form ([AWS](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)). Then send it a prompt in the playground.
- [ ] Check the Explore AWS widget on Console Home. Creating a budget and using the Bedrock playground are two of five activities worth $20 in credits each ([AWS](https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier-credits.html)).

Credits may not cover Marketplace charges, so check Billing, Credits after your first Claude calls. Budget as if Claude usage lands on your card.

### Install your tools (about 2 hours)

| Tool | Why | Check it works |
| --- | --- | --- |
| AWS CLI v2 | Talk to AWS from the terminal | `aws --version` |
| Node.js 20+ | Runs the CDK and AgentCore CLIs | `*node --version*` |
| AWS CDK v2 | Infrastructure as code | `npm i -g aws-cdk`, then `cdk --version` |
| AgentCore CLI | Deploys your agents | `npm i -g @aws/agentcore`, then `agentcore --version` |
| Python 3.12 | Lambdas, agents, scripts | `python3 --version` |
| Docker Desktop | Builds Lambda container images | `docker run hello-world` |
| FFmpeg | Test clip commands locally | `ffmpeg -version` |
| Git and a GitHub account | Version control and portfolio | `git --version` |
| VS Code | Where you edit files; `code` opens them from the terminal | `code --version`. Windows: add Microsoft's WSL extension in VS Code. Mac: Cmd+Shift+P → Shell Command: Install 'code' command in PATH |

On Windows, do everything inside WSL2 (Ubuntu). On an Apple Silicon Mac, build your Lambdas for ARM64 so Docker doesn't have to emulate x86.

### Connect the CLI with single sign-on (30 minutes)

This step connects the terminal on your own computer to your AWS account. Afterwards the AWS CLI, `cdk` and `agentcore` act as the Identity Center user you just made, with no passwords or access keys saved on your laptop. You do it once, in a terminal on your computer (the Ubuntu app if you're on Windows with WSL, or Terminal on a Mac), not on the AWS website. It needs the AWS CLI from the tools table above.

1. **Get your portal URL.** In the AWS console, open IAM Identity Center, then Dashboard. Under Settings summary, copy the **AWS access portal URL**. It looks like `https://d-xxxxxxxxxx.awsapps.com/start`.
2. **Run `aws configure sso`** in your terminal and answer its questions:

| It asks | You type |
| --- | --- |
| SSO session name | `clip` |
| SSO start URL | the portal URL from step 1 |
| SSO region | `us-east-1` |
| SSO registration scopes | `sso:account:access` |
| (a browser tab opens) | sign in as your Identity Center user, complete MFA, click **Allow access** |
| Account and role | your account and `AdministratorAccess` (the CLI picks them for you if there's only one of each) |
| Default client Region | `us-east-1` |
| CLI default output format | `json` |
| Profile name | `clip` |

If no browser opens, which is common in WSL, paste the link the terminal prints into your browser, or run `aws configure sso --use-device-code` and enter the code it shows ([AWS](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html)).

3. **Use the profile and test it.** Run `export AWS_PROFILE=clip`, then `aws sts get-caller-identity`. It worked if you see your 12-digit account ID and an ARN containing `AWSReservedSSO_AdministratorAccess`. Add the `export` line to the end of `~/.bashrc` (`~/.zshrc` on a Mac) so new terminals use it automatically.

To add that line from the terminal, run `echo 'export AWS_PROFILE=clip' >> ~/.bashrc` once (on a Mac, change `~/.bashrc` to `~/.zshrc`). Every terminal you open afterwards uses the `clip` profile.

The code block below is the same steps in short form. The `#` lines are the questions and your answers, not commands to type. You only need `aws sso login --profile clip` later, when a command says your session has expired.

```bash
aws configure sso
# SSO session name: clip
# SSO start URL: your access portal URL (from Identity Center)
# SSO region: us-east-1
# Pick your account and the AdministratorAccess role
# Default region: us-east-1   Profile name: clip

aws sso login --profile clip
export AWS_PROFILE=clip
aws sts get-caller-identity   # prints your account and role
```

No access keys ever touch your disk. Sessions expire, so run `aws sso login` again when a command says your token has expired.

### Create the repo and your first stack (about 3 hours)

**Terminal**, one line at a time. These make the project folder, create the CDK app in `infra`, switch on its Python environment and prepare your account for CDK (the bootstrap). `cdk init` also makes an inner `infra/infra/` folder, which is where your stack files go.

```bash
mkdir clip-agent && cd clip-agent && git init
mkdir infra services agents evals docs
cd infra
cdk init app --language python
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```

- [ ] Repo created and pushed to a private GitHub repo.
- [ ] CDK bootstrapped in us-east-1.

**Deploy your first stack.** A stack is a set of AWS resources that CDK creates and updates together. This one keeps all media in one S3 bucket, under prefixes (`raw/`, `transcripts/`, `kb/`, `previews/`, `renders/`), and all state in one DynamoDB table. You write it in two Python files, then deploy it.

- [ ] **1. Create the stack file.** **Terminal**, from your project folder:

```bash
cd ~/clip-agent
code .
code infra/infra/storage_stack.py
```

The first `code` opens your project in VS Code. If it asks whether you trust the authors of these files, choose **Yes**, and keep that window open while you work. The second opens an empty tab for the new file, in the inner `infra` folder next to the `infra_stack.py` example that `cdk init` made (you won't use that one). Paste this whole box into the tab, then save with Ctrl+S (Cmd+S on a Mac):

```python
# infra/infra/storage_stack.py
from aws_cdk import Stack, Duration, RemovalPolicy, aws_s3 as s3, aws_dynamodb as ddb
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.media = s3.Bucket(
            self, "Media",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            event_bridge_enabled=True,  # uploads become EventBridge events in week 2
            lifecycle_rules=[
                s3.LifecycleRule(prefix="raw/", expiration=Duration.days(14)),
                s3.LifecycleRule(prefix="previews/", expiration=Duration.days(7)),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.table = ddb.TableV2(
            self, "State",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing=ddb.Billing.on_demand(),
            removal_policy=RemovalPolicy.RETAIN,
        )
```

`BLOCK_ALL` keeps the bucket private, and `event_bridge_enabled` lets an upload start the pipeline in week 2. The lifecycle rules delete raw videos after 14 days and previews after 7, and `RETAIN` keeps your data even if the stack is deleted.

- [ ] **2. Replace `infra/app.py`.** This is the outer `app.py`, next to `cdk.json`: it lists the stacks CDK deploys. **Terminal:** `code infra/app.py`, then in VS Code select everything with Ctrl+A (Cmd+A), paste this box over it, and save:

```python
# infra/app.py
import os

import aws_cdk as cdk

from infra.storage_stack import StorageStack

app = cdk.App()
env = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="us-east-1")
storage = StorageStack(app, "ClipStorage", env=env)
cdk.Tags.of(app).add("project", "clip-agent")
app.synth()
```

- [ ] **3. Check it.** **Terminal:**

```bash
cd ~/clip-agent/infra
source .venv/bin/activate
cdk synth ClipStorage
```

A page of YAML means your code is fine: it's the CloudFormation template CDK made from your Python. An error names the file and line to fix, usually a paste into the wrong file or lost indentation.

- [ ] **4. Deploy it.** **Terminal**, same folder:

```bash
cdk deploy ClipStorage
```

It lists the IAM changes and asks `Do you wish to deploy these changes (y/n)?`. Type `y` and press Enter. After a minute or two it prints `✅  ClipStorage`.

- [ ] **5. See what you built.** **Console:** S3 → Buckets shows `clipstorage-media…`, and DynamoDB → Tables shows `ClipStorage-State…`. CloudFormation → Stacks → ClipStorage → Resources lists everything the stack made, including a small helper Lambda that switches on the bucket's EventBridge events.
- [ ] **6. Save your work.** **Terminal:**

```bash
cd ~/clip-agent
git add .
git commit -m "Week 1: storage stack"
git push
```

If `git push` asks for a username or password, click **Sync Changes** in VS Code's Source Control panel instead.

### Set up Claude Code (about 1 hour)

Claude Code writes and explains the code, and you do the console work and deploys. These steps make that split enforced rather than a promise. The starter kit from our chat holds the configuration, and `docs/claude-code-workflow.md` inside it covers how to run each session.

- [ ] **1. Install the extensions.** **VS Code:** press Ctrl+Shift+X (Cmd+Shift+X on a Mac), search **Claude Code** and install the one published by Anthropic, then search **AWS Toolkit** and install that too. On Windows the bottom-left corner should say **WSL: Ubuntu**; if an extension offers **Install in WSL**, click that.
- [ ] **2. Sign in.** **VS Code:** in the window with your project open (its Explorer lists `infra` and `services`), open any file, such as `infra/app.py`, and click the Spark icon at the top right of the editor. Click **Sign in** and finish in your browser with your Claude account. Claude Code needs a paid plan, such as Pro.
- [ ] **3. Start every conversation in plan mode.** **VS Code:** open Settings (Ctrl+, or Cmd+,), stay on the **User** tab, search `initial permission mode`, and set **Claude Code: Initial Permission Mode** to `plan`. Claude then shows you a plan and waits for your OK before it changes files. Pro and Max plans otherwise start in Auto mode, which acts without asking ([docs](https://code.claude.com/docs/en/permission-modes)).
- [ ] **4. Install the Claude Code CLI too**, so `claude` also works in the terminal ([docs](https://code.claude.com/docs/en/setup)). **Terminal:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Open a new terminal and run `claude --version`. It prints a version number. On a Mac, if it says `command not found`, run `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc` and open a new terminal.

- [ ] **5. Give Claude a read-only AWS profile.** Claude's terminal uses this profile, so it can read logs and settings but can't change anything in your account. **Console**, in IAM Identity Center:
  1. **Permission sets → Create permission set →** choose **Predefined permission set** and **ReadOnlyAccess → Next → Next → Create**.
  2. **AWS accounts →** tick your account **→ Assign users or groups →** on the **Users** tab tick your user **→ Next →** tick **ReadOnlyAccess → Next → Submit**.

Then **Terminal:**

```bash
aws configure sso --profile clip-readonly
```

Keep `--profile clip-readonly` in the command. It names the new profile, and without it the command would overwrite your `clip` profile, because your terminal already uses that one. For the session name, type `clip` again, then press Enter at the next three questions to keep last time's answers. Sign in if a browser opens, choose **ReadOnlyAccess** when it lists roles, then answer `us-east-1` and `json`. Check it:

```bash
aws sts get-caller-identity --profile clip-readonly
```

It worked if the ARN contains `AWSReservedSSO_ReadOnlyAccess`.

- [ ] **6. Add the starter kit to your repo.** Download `clip-agent-kit-v2.zip` from our chat. It holds `CLAUDE.md`, the `.claude/` settings and a copy of this guide. **Terminal** on Windows, where `ls /mnt/c/Users/` shows your Windows user name (if it has a space, put the whole zip path in quotes):

```bash
cd ~/clip-agent
sudo apt install -y unzip
unzip -o /mnt/c/Users/YOUR_WINDOWS_USER/Downloads/clip-agent-kit-v2.zip
```

On a Mac:

```bash
cd ~/clip-agent
unzip -o ~/Downloads/clip-agent-kit-v2.zip
```

If Safari already unzipped it into a `clip-agent-kit-v2` folder in Downloads, run `cp -R ~/Downloads/clip-agent-kit-v2/. ~/clip-agent/` instead.

`ls -a` now shows `CLAUDE.md`, `.claude`, `.mcp.json`, `.gitignore` and `docs` next to `infra`. Save it:

```bash
git add .
git commit -m "Add Claude Code kit"
git push
```

- [ ] **7. Check it works.** **VS Code:** start a new Claude Code conversation (Ctrl+Shift+P, or Cmd+Shift+P on a Mac, then **Claude Code: Open in New Tab**) and try three things:
  - Type `/mcp`. `aws-knowledge` should show as connected. If Claude asks whether to use the project's MCP servers, say yes.
  - Type `/`. The list should include `/step`, `/console`, `/explain` and `/diagnose`.
  - Ask "What are you not allowed to do in this repo?" The answer should match `CLAUDE.md`: no deploys, no `--profile clip`, no `git push`.

From now on, start each build session with `/step`, the week and the step name, for example `/step 2 Build the FFmpeg Lambda`. `docs/claude-code-workflow.md` covers the rest.

### Clip by hand and start earning (about 6 hours)

- [ ] Pick one niche, such as business podcasts, and create an account for it on TikTok, YouTube, Instagram (switch it to a professional Business account) and X.
- [ ] Warm the accounts up: 15–20 minutes a day of watching and engaging in your niche, and at most one post a day this week.
- [ ] Sign up to Whop, Vyro and Crayo Content Rewards. Pick 2–3 campaigns with budget left and clear rules, and save each brief as a text file.
- [ ] Make 10–15 clips by hand in Crayo (Hobby plan, $19) or CapCut, post them, and submit each link straight away.
- [ ] Log every clip in a spreadsheet: campaign, platform, hook line, length, minutes spent, views at 24 hours and 7 days, payout.
- [ ] Mark the 5 best moments (start and end times) in 3 source videos and save them as `evals/labels.json`. These become your ground truth in week 8.

For the last box, create the file with `code evals/labels.json` from `~/clip-agent`. Each key is a video's file name, and `start` and `end` are seconds from the start of that video, so 5:12 is `312`:

```json
{
  "ep1.mp4": [
    {"start": 312, "end": 345},
    {"start": 1210, "end": 1248}
  ],
  "ep2.mp4": [
    {"start": 95, "end": 130}
  ]
}
```

List five moments for each video, with a comma after every `}` except the last one in each list.

**Done when:** `aws sts get-caller-identity` works through SSO, your bucket and table show up in the console, at least 5 clips are submitted, and your first Sunday demo is recorded.

**Escape hatch:** if Identity Center blocks you for more than 90 minutes, run CLI commands from CloudShell in the console for now and come back to SSO midweek.
