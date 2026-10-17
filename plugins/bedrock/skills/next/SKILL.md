---
name: next
description: Status navigator — what is done, what is left, who is waited on, can the owner rest. Use for "что дальше", "всё сделал?", "можно чиллить?", "what's next", "where are we".
---

# Navigator

Answers the owner's recurring status questions from files, never from memory (D014, D042).

## Triggers
- RU: «что дальше», «всё сделал?», «что осталось», «можно чиллить?»
- EN: "what's next", "are we done", "what's left", "can I rest"

## 1. Read the state
Read, in this order, and stop reading once the answer is clear:
1. `bedrock backlog list` (open tasks, priority, claims) and `bedrock backlog next`.
2. The project status note: `~/projects-memory-bank/<project>/status.md`, and the plan of the
   open block (`~/projects-days/<project>/<date>/<block>/plan.md`).
3. Today's day log: `bedrock minutes <block> --open` for the current block, and the log file
   under `~/projects-days/<project>/<work-date>/log.jsonl`.
4. `git status` and `git log --oneline -10` in the workspace.
5. Other sessions in this project: the SessionStart context lists them.
6. Unclosed blocks: a block with `taken` and no `closed` in any day's log.

Done when: every line of the answer below rests on one of these reads.

## 2. Answer in a fixed shape (Russian, plain words)
```
Сделано: <what changed for the product, one line each>
Осталось: <open tasks, most urgent first, with P0–P3>
Ждём: <who or what, and what unblocks it>
Можно отдыхать: <да / нет — one reason>
```
- "Можно чиллить?": the reply opens with one word, «да», «нет» or «не знаю», then one reason
  (D021). «не знаю» is right when the state cannot be read.
- Nothing is called done that was not checked; say "не проверено" instead.
- No PR numbers, hashes or file lists unless asked (D021).

Done when: the four lines are written and each claim has its source in the reads above.

## 3. Offer the next step
- One line: the next task and who does it (session or agent).
- If the next task needs the owner (a grant, a decision, a login), give the exact step:
  the command, where to click, what to send back.

Done when: the line is sent.

## Skill map (when the owner asks "что ты умеешь")
| When | Skill | How to tell it worked |
|---|---|---|
| A new request or task | `day` | a plan file, then commits per task |
| A bug | `debug` | a cause record and a red-then-green test |
| A review of a change | `review` | findings fixed, one summary line |
| A question about the project | `ask` | answer with source and confidence |
| Ending a session or a phase | `handoff` | a handoff note in the base |
| Notes, decisions, failures | `kb` | `bedrock kb validate` clean |
| Writing skills, agents, briefs | `writing` | `skillcheck.py --strict` clean |
| Breaking green code on purpose | `hunt` | findings reproduced or cut |
| Checking flows in a browser | `e2e` | scripted tests for each finding |
| A call to debrief | `call` | `bedrock call quotes` prints `[]` |
| A report or PDF for people | `doc` | the PDF, `bedrock text check` clean |
| A message in the owner's voice | `humanize` | copy-ready text, `bedrock text check` clean |
| Bug reports to sort | `triage` | one decision per group |
| The weekly look back | `retro` | small fixes logged, a list for «го» |
| Architecture review (on request) | `arch` | three designs, a decision note |
| Work while the owner sleeps | `night` | a morning report |
| A new or existing project | `start` | `bedrock project check` prints `[]` |
| Granting an action, all-out, withdrawing | `allow`, `unleash`, `revoke` | the hook's notice |
| Auditing code for bugs, security, speed | `code-review` | a report that passes its receipt check |
| Designing or rebuilding a web interface | `design-creator` | its quality gate passes |
