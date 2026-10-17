---
name: night
description: Autonomous work until morning — a pre-sleep check, the allowed list, auto-continue with fuses, a watchdog, a morning report. Use for "автономно до утра", "поработай ночью", "work overnight".
---

# Working overnight

The owner goes to sleep. In the morning the work is done or each stop is explained. The
session is never idle (D046).

## Triggers
- RU: «автономно до утра», «поработай ночью»
- EN: "work overnight", "keep going while I sleep"

## 1. The start phrase
The owner says what is allowed, in his own words, for example «автономно до утра: можно
пушить в ветки, нельзя деплой». Those words become the grant (D016). Nothing outside them
happens. The end defaults to 12:00 local.

## 2. The pre-sleep check (one message, before he leaves)
1. Sessions that must live until morning (cloud logins, GitHub, VPN) and when each expires:
   «AWS истекает в 03:00, обнови сейчас».
2. Enough work for the night: the plan or the listed tasks, plus the fallback queue (step 4).
3. Tasks that need the owner moved to the end or set aside.
4. Enough subscription limit for the night.
Only «готово к ночи» lets him go.
Done when: that line is sent.

## 3. Set it running
- `bedrock session set autocontinue.until=<ISO end, UTC>` and the first task in
  `autocontinue.next`, as in the `day` skill.
- Start Claude under the watchdog, which restarts a crash and stops at the end time:
  `bedrock night watch --until 12:00 -- claude --continue`.
- All guards stay on. One commit per task. Progress lives in files.
Done when: the watchdog is running.

## 4. Never idle
- A blocked task: mark it with the reason and a step-by-step instruction for the owner
  (D021), then start the next independent task.
- Main list done or blocked: the fallback queue inside the grant: refresh stale notes, add
  tests where coverage is thin, R1 and R2 backlog items marked "ok at night".
- A network or flaky failure is retried with a pause, not treated as a stop.
- Stop only when nothing is left or a limit is reached.

## 5. Waking the owner
A phone notification only for P0 or a decision that blocks everything (`bedrock notify p0`
or `bedrock notify blocked`). Everything else waits for the morning.

## 6. The morning report
Plain text: what got done, what was left and why, the one question for the owner, the limit
spent. The first night runs a small list; the morning looks at what misbehaved.
