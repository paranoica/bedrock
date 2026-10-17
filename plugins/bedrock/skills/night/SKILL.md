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
пушить». Those words become the grant (D016), «до утра» meaning until 12:00 local. Nothing
outside them happens. Words grant only when the message holds nothing but the grant: any
other word («деплой нельзя», «после ревью») voids it, and `/bedrock:allow push until 12:00`
gives it exactly. A grant from words has no target: a push grant covers any branch.
Done when: the prompt hook's notice «bedrock: grant from your words: …» names exactly the
allowed actions and their end. Anything else means rephrase, or use `/bedrock:allow`.

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
- The owner closes this session and, in his terminal, starts Claude under the watchdog,
  which restarts a crash and stops at the end time:
  `bedrock night watch --until 12:00 -- claude --continue "продолжай ночной план"`.
  The prompt makes a restarted session pick the plan up instead of waiting for input. The
  watchdog also lifts Claude Code's cap on Stop-hook blocks in a row
  (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 8 by default) to 60, so bedrock's own fuses stop first.
- All guards stay on. One commit per task. Progress lives in files.
Done when: the watchdog is running.

## 4. Never idle
- A blocked task: mark it with the reason and a step-by-step instruction for the owner
  (D021), then start the next independent task.
- Main list done or blocked: the fallback queue inside the grant: refresh stale notes, add
  tests where coverage is thin, R1 and R2 backlog items marked "ok at night".
- A network or flaky failure is retried with a pause, not treated as a stop.
- Stop only when nothing is left or a limit is reached (D056). At 80% of the 5-hour window
  with no answer from the owner, the agent guard saves: only review agents start. At 95%
  agents stop, the session finishes its step, writes a handoff and pauses until the window
  resets. The watchdog brings it back after the reset.
Done when: every stopped task has its reason and the owner's steps in the status note.

## 5. Waking the owner
A notification only for P0 or a decision that blocks everything. With Remote Control
connected, a phone push through the PushNotification tool. Otherwise a desktop one:
`bedrock notify p0 "<title>" "<what is needed>"`, or `blocked` in place of `p0`. Everything
else waits for the morning.
Done when: no other notification was sent.

## 6. The morning report
Plain text: what got done, what was left and why, the one question for the owner, the limit
spent. The first night runs a small list; the morning looks at what misbehaved.
Done when: the report is the first thing the owner sees in the session.
