---
description: Review code I wrote myself, giving hints before answers.
argument-hint: "<file or function I wrote>"
disable-model-invocation: true
---

I wrote this myself: $ARGUMENTS

Review it the way a senior engineer mentors a junior.

- Check in this order: correctness, security (IAM scope, input validation, secrets, prompt injection), AWS best practice, then style.
- For each issue, start with a hint or a question. Show the fix only if I ask, or straight away if it's a security problem.
- Say specifically what I did well.
- Don't edit the file.
