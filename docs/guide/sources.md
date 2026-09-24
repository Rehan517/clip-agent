> Reference copy of the build guide, exported 24 Sep 2026. The living doc is the source of truth and tracks progress: https://claude.ai/code/artifact/f66041c7-114a-4c2e-be32-f922f5293e7e
> Checkbox state here means nothing; ask Rehan which step he's on.

## Sources

Every page below was opened for this guide on 23 September 2026. The Python and CDK snippets were compiled and synthesised against aws-cdk-lib 2.270, strands-agents 1.57 and bedrock-agentcore 1.23, and the FFmpeg commands were run on test video. The Docker images and AWS calls still need your account to test.

### AWS account, pricing and limits

- [AWS: Choosing a Free Tier plan](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
- [AWS: Earn additional Free Tier credits](https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier-credits.html)
- [AWS: Free Tier FAQs](https://aws.amazon.com/free/free-tier-faqs/)
- [AWS: Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)
- [AWS: Transcribe pricing](https://aws.amazon.com/transcribe/pricing/)
- [AWS: Transcribe input formats](https://docs.aws.amazon.com/transcribe/latest/dg/input.html)
- [Caylent: Amazon Bedrock pricing explained](https://caylent.com/blog/amazon-bedrock-pricing-explained)

### Bedrock models and knowledge bases

- [AWS Security Blog: Simplified Bedrock model access](https://aws.amazon.com/blogs/security/simplified-amazon-bedrock-model-access/)
- [AWS: Claude Sonnet 5 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5.html)
- [AWS: Claude Haiku 4.5 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html)
- [AWS: Create a knowledge base](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [AWS: S3 Vectors with Bedrock Knowledge Bases](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html)
- [AWS: Querying multimodal knowledge bases](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-multimodal-test-and-query.html)
- [AWS ML Blog: Video search with Marengo 3.0](https://aws.amazon.com/blogs/machine-learning/video-and-image-search-in-amazon-bedrock-knowledge-base-using-marengo-3-0/)

### AgentCore and Strands

- [AWS: Get started with the AgentCore CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html)
- [AWS: Use any agent framework with AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html)
- [AWS: Getting started with AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-getting-started.html)
- [AWS: AgentCore Gateway quick start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-quick-start.html)
- [AWS: Gateway Lambda targets](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-lambda.html)
- [AWS: Getting started with Policy in AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-getting-started.html)
- [AWS: Policy in AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)
- [GitHub: AgentCore CLI](https://github.com/aws/agentcore-cli)
- [GitHub: bedrock-agentcore Python SDK](https://github.com/aws/bedrock-agentcore-sdk-python)
- [PyPI: strands-agents](https://pypi.org/project/strands-agents/)
- [Strands: Structured output](https://strandsagents.com/docs/user-guide/concepts/agents/structured-output/)
- [Strands: Amazon Bedrock provider](https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/)
- [Strands: AgentCore Memory session manager](https://strandsagents.com/docs/integrations/session-managers/agentcore-memory/)
- [ClawAWS: AgentCore Cedar policy examples](https://clawaws.com/blog/agentcore-cedar-policy-examples/)

### Tools and APIs

- [Docker Hub: mwader/static-ffmpeg](https://hub.docker.com/r/mwader/static-ffmpeg)
- [Upload-Post: Upload video API](https://docs.upload-post.com/api/upload-video)
- [Upload-Post: API reference for LLMs](https://docs.upload-post.com/llm.txt)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [GitHub: configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
