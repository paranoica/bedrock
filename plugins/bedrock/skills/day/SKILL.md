---
name: day
description: The working loop for a task or request — intake, plan, critic, cut, implement, review, deliver, close. Use for any new task, feature, fix or request, and for "начинаем день".
---

# The working loop

One block = one task from "taken" to "done and merged" (D031). Each step ends on a check.
Guards (git, grants, secrets, agents, heavy runs) are hooks; this skill never restates them.

## Triggers
- RU: «сделай X», «новая задача», «начинаем день», «закрываем день»
- EN: "build X", "fix X", "new task", "start the day", "close the day"

## 0. Start of day (once per work day)
Follow `references/start-of-day.md`. Done when the owner has the three-line summary
"вчера / входящие / сегодня".

## 1. Intake
- Size the request: R1 (no logic), R2 (ordinary code), R3 (risky or new), and P0–P3 (D032).
- P0 goes to the urgent path in `references/urgent.md` and skips the plan.
- Look facts up instead of asking; ask only what changes the result, in one message, at most
  five questions, each with a default and the cost of a wrong default (D033).
- Log it: `bedrock log taken --block <id> --detail "<R/P> <title>"`.

Done when: R, P and the questions (or "no questions") are written in the plan file.

## 2. Plan
- R1: no plan. R2: a short plan. R3: a full plan with a design section (D035).
- Write it from `references/plan.md` to `~/projects-days/<project>/<date>/<block>/plan.md`.
- Every plan has: done-when (checkable), assumptions, files, tests named with what they
  assert, tasks with who and model, estimate, out of scope.
- Research per `references/research.md` when the plan rests on library behaviour (D034).

Done when: the plan file exists and its done-when is a test, a command or a number.

## 3. Critic
- R2: one critic agent; R3: two critics on different models (D036). Brief from the
  plugin's `templates/briefs/brief.md`; give it the plan, done-when, decisions, code rules.
- Take each finding with evidence or drop it; a blocker is re-read in the code first.
- At most two rounds; a second round with no fewer blockers goes to the owner.
- Tell the owner only the delta: "критик: 5 найдено, 3 принято, +20 мин".

Done when: the plan file has a "Critic" section with taken and dropped findings.

## 4. Owner's go
- Show the plan in five lines and wait for «го» (one go covers the whole plan, D016).
- Then: `bedrock log plan-approved --block <id>` and
  `bedrock session set task="<title>" plan='[0,<n>]' estimate_min=<m> state=work`.

Done when: the log line exists and the status line shows the task.

## 5. Cut into tasks
- One task = one commit with its own test, about 30–40 minutes of human work, its own files
  (D037). Add each with `bedrock backlog add '<json>'`.
- Set auto-continue for the next safe task:
  `bedrock session set autocontinue='{"next": {"id": "T2", "title": "...", "safe": true}}'`.

Done when: every task is in the backlog with files, test, who and estimate.

## 6. Implement each task
Follow `references/implement.md` (D039): a failing test first, minimal code, verify after
every few edits, refactor only while green, read the diff yourself, commit.

Done when: the task's test failed before and passes now, and the commit exists.

## 7. Review
Use the `review` skill for every R2/R3 block: code review plus plan-compliance review,
rounds until nothing real is found (D050).

Done when: the review summary line is written and `bedrock review pass <branch>` is recorded.

## 8. Deliver
Follow `references/deliver.md`: branch and PR per the project, live verification, and every
outward step only under the owner's grant (D052, D053).

Done when: the change is checked live, or the report says plainly that it was not.

## 9. Close the block
- `bedrock log closed --block <id>` and `bedrock minutes <id>` into the report.
- Update the knowledge base for every module touched (the Stop hook asks once).
- Report to the owner in plain Russian (D021): what changed for the product, checked live
  or not, what is needed from the owner, what is next.
- `bedrock session set state=null task=null plan=null autocontinue=null`.

Done when: the log line, the base update and the report are all done.

## End of day
`references/start-of-day.md` § End of day. Done when the owner has the day summary.
