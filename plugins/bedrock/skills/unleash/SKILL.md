---
name: unleash
description: The owner turns on all-out mode for this project until a time; every guard still logs.
disable-model-invocation: true
---

# All-out mode

The prompt hook has already recorded the mode (D016). Its notice shows until when.

## Triggers
- RU: «/bedrock:unleash до утра»
- EN: "/bedrock:unleash until 18:00"

## What to do
Say in one line, in Russian, that all-out mode is on and when it ends, from the hook's notice,
and what it never covers: deploys to production and sending messages. Words like «деплой
нельзя» in the same message are not read by the mode: if the owner wrote any, say so and
suggest `/bedrock:revoke` and single `/bedrock:allow` grants instead.
Done when: the line is sent.
