---
description: Walk me through doing something in the AWS console myself, explaining each setting.
argument-hint: "<what to create or inspect>"
disable-model-invocation: true
---

I want to do this in the AWS console myself: $ARGUMENTS

1. First, check whether CDK manages this resource in our repo. If it does, say so up front: I should only inspect it in the console, because the next `cdk deploy` overwrites console edits. Suggest a throwaway version I can practise on instead, and mention Console-to-Code if the service supports it.
2. Say where to go (service, us-east-1, which page) and what the service does, in one line.
3. Give numbered clicks and fields. For each setting that matters, say what it does and what to choose for this project. Flag anything that costs money.
4. List what to copy afterwards (IDs, ARNs, names) and where it goes in the repo, usually the constants at the top of `infra/infra/pipeline_stack.py`.
5. Say how to check it worked.

If the console may have changed recently, check the `aws-knowledge` MCP docs. Don't run AWS commands to do it for me.
