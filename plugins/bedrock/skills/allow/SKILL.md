---
name: allow
description: The owner grants one action, e.g. /bedrock:allow push, until a time or the end of the plan.
disable-model-invocation: true
---

# Allow one action

The prompt hook has already read the owner's words and recorded the grant (D016). Its notice
«bedrock: grant from your words: …» shows what was granted and until when.

## Triggers
- RU: «/bedrock:allow push до 18:00»
- EN: "/bedrock:allow merge until the end of the plan"

## What to do
Say in one line, in Russian, what is now allowed and until when, from the hook's notice. No
notice means nothing was granted: say so, and show the form
`/bedrock:allow <push|merge|pr|deploy> [target] [until HH:MM | until the end of the plan]`.
Done when: the line is sent.
