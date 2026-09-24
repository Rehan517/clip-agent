---
paths:
  - "infra/**/*.py"
---

# CDK rules

- Grant access with construct methods such as `bucket.grant_read`, `table.grant_read_write_data`, `secret.grant_read` and `machine.grant_task_response`. Write a `PolicyStatement` only when no grant method exists, and scope its `resources`.
- After changing a stack, run `cdk synth` and summarise what changed: new resources, new IAM statements, and anything CloudFormation will replace or delete. Call out replacements loudly, because they can lose data.
- Keep `RemovalPolicy.RETAIN` on the media bucket, the state table and the evidence bucket.
- Never hardcode the account ID. Use `self.account` and `self.region`.
- Resources Rehan creates in the console (knowledge bases, agent runtimes, AgentCore memory, secrets) are referenced by ID or name, never created in CDK unless he asks.
- When the state machine changes, describe it as a list of states and transitions, and name the pattern used: polling loop, Map, or task-token callback.
