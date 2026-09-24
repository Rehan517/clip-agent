> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## When you get stuck

Most blockers in this build are one of about twenty known errors. Check the table first, then the failed step's input and logs, and after 90 minutes take the escape hatch or ask.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `command not found` just after installing something | The terminal was opened before the install | Open a new terminal and try again |
| `code: command not found` | VS Code's `code` command isn't set up for this terminal | Windows: install VS Code's WSL extension, then open a new Ubuntu terminal. Mac: in VS Code, Cmd+Shift+P → Shell Command: Install 'code' command in PATH |
| `No such file or directory` | The terminal is in a different folder from the one the step uses | Run `pwd` to see where you are, then the step's `cd` line |
| `ModuleNotFoundError: No module named 'aws_cdk'` | The Python environment isn't on in this terminal | `cd ~/clip-agent/infra`, then `source .venv/bin/activate` |
| `Unable to locate credentials`, or CDK can't resolve your account | This terminal has no AWS profile set | `export AWS_PROFILE=clip`, and add it to `~/.bashrc` as in the SSO step |
| `Cannot connect to the Docker daemon` or `docker: command not found` | Docker Desktop isn't running, or its WSL integration is off | Start Docker Desktop; on Windows, turn on Settings → Resources → WSL integration for Ubuntu |
| Telegram says `chat not found` | Wrong chat ID in `clip/telegram`, or you never messaged the bot | Message the bot, check `getUpdates` again, and fix the secret |
| "Token has expired" on any AWS command | Your SSO session timed out | `aws sso login --profile clip` |
| `cdk deploy` says the environment isn't bootstrapped | CDK hasn't been set up in us-east-1 | `cdk bootstrap aws://ACCOUNT_ID/us-east-1` |
| Docker build shows `exec format error` or crawls | Image architecture doesn't match the Lambda | Set `ARCH` and `PLATFORM` both to ARM64 or both to x86 |
| Lambda rejects memory above 3,008 MB, or runs get throttled | New accounts start with reduced quotas ([AWS](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)) | Stay at 3,008 MB and request increases in Service Quotas |
| `AccessDeniedException` when calling Claude | Use-case form not submitted, or the free plan blocks the Marketplace offer | Submit Anthropic's form, upgrade to the Paid plan, try once in the playground |
| Transcribe job fails on the media URI | Odd characters in the S3 key, or the file is too large or long | Rename with letters, numbers and dashes; keep files under 4 hours |
| `ConflictException` from a knowledge base sync | Another sync is running on that data source | Already handled: Step Functions retries every 60 seconds |
| `ReadTimeoutError` when calling an agent | boto3's default 60-second read timeout | Use the client with `Config(read_timeout=900)` from the snippets |
| `UnknownServiceError: bedrock-agentcore` in a Lambda | The runtime's bundled boto3 is older than the API | Bundle a newer boto3 with that function, or use a container image |
| Captions missing from renders | No fonts in the Lambda image | Keep `fonts/` copied into the image and `fontsdir=` in the filter |
| Telegram buttons spin forever | The webhook failed, or it didn't answer the callback | Read the webhook's CloudWatch logs; `getWebhookInfo` shows Telegram's last error |
| Telegram can't fetch a video | The presigned link expired, or the file is over about 20 MB | Keep previews at 540x960 and CRF 28; regenerate the link |
| Step Functions says a JSONPath could not be found | A field is missing from that state's input | Open the failed state's input in the console and compare it with the path |
| An agent tool gets `AccessDenied` | The runtime role lacks that permission | Check `AGENT_ROLE_NAME` matches the runtime's role, then redeploy |
| Object Lock upload fails asking for a checksum | Object Lock buckets require one | Pass `ChecksumAlgorithm="SHA256"` to `put_object` |
| TikTok posts never go live | `MEDIA_UPLOAD` sends drafts to your TikTok inbox | Finish them in the app, which also lets you add a trending sound |

### Asking for help

- **Write the question well:** the step you're on, the exact command or code, the full error, and what you expected. Half the time, writing it down solves it.
- **Where to ask:** AWS re:Post (tag the service), the Strands Agents GitHub discussions, the AgentCore samples repository, or me, with the error pasted in.
- **Local help:** an AWS user group meetup in Melbourne is a good place to show the project and get unstuck in person.
