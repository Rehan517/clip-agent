---
description: Start a build-guide step. Explain the concept, plan it, then build it with me in small pieces.
argument-hint: "<week number> <step name>"
disable-model-invocation: true
---

We're starting this step of the build guide: $ARGUMENTS

1. Read only `docs/guide/week-$0.md` and find the matching step, plus any repo files that step touches.
2. Teach first, briefly:
   - What we're building and where it fits in the pipeline (2 or 3 sentences).
   - Each AWS concept involved, in one line, with its interview or exam name where there is one.
   - A numbered list of what I do myself (console, deploys, tests) and what you'll write.
3. Give a short plan: the files you'll create or change, and how we'll test the result.
4. Stop and wait for me to say "go". Then build in small pieces and explain each one as you go.
5. Finish with the test commands, the guide's "Done when" for this week, and the checkbox I can tick.
