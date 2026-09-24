---
description: Explain the current uncommitted changes, or a named file, well enough that I could explain them in an interview.
argument-hint: "[file path, or leave empty for the current changes]"
disable-model-invocation: true
---

## Current changes

!`git status --short`

!`git diff`

Explain $ARGUMENTS. If that's empty, explain the changes above.

- The purpose of each changed file, in one line.
- The non-obvious lines: what they do and why they're written that way.
- Every AWS API call it makes, the IAM permission each needs, and where that permission is granted.
- How it fails (timeouts, retries, bad input) and where I'd see the failure: CloudWatch Logs, the Step Functions graph, or Telegram.
- Two questions an interviewer might ask about this code.

Don't change any files.
