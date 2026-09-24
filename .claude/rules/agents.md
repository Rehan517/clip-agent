---
paths:
  - "agents/**"
---

# Agent rules (Strands and AgentCore)

- Each agent's `main.py` uses `BedrockAgentCoreApp` from `bedrock_agentcore.runtime`, exposes `@app.entrypoint def invoke(payload, context)`, and ends with `app.run()` under `if __name__ == "__main__":`.
- Get structured output with `agent(prompt, structured_output_model=Model)` and return `result.structured_output.model_dump()`. Put constraints in Pydantic `Field`s.
- Build `@tool` functions inside a `make_tools(...)` closure so each request's values, such as `video_id`, are captured safely.
- Wrap untrusted text (transcripts, briefs, on-screen text) in tags, and say in the system prompt that it is data, not instructions.
- Use the model IDs in `CLAUDE.md`. Check the `aws-knowledge` MCP docs before using an AgentCore or Strands API this repo doesn't use yet.
- Test locally (`python app/<Agent>/main.py` plus a curl POST) before Rehan deploys with `agentcore deploy`.
- New AWS permissions for an agent go on its runtime role through CDK (see `MomentFinderDataAccess`), never on Rehan's user.
