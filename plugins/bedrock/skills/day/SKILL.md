---
name: day
description: The working loop for any task — intake, plan, critic, cut, implement, review, deliver. Use first for every new task, feature or change: "надо добавить", "сделай", "build X", "начинаем день".
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
- Look facts up instead of asking. Questions depend on the risk (D033):
  - R1: none.
  - R2: only when the scope is genuinely unclear. One message, at most five questions, each
    with a default and the cost of a wrong default.
  - R3 or a new feature, when the owner says «грилл» or the task is murky: an interview, one
    question at a time, each answer saved to the plan file at once. Otherwise as R2.
- Log it: `bedrock log taken --block <id> --detail "<R/P> <title>"`.

Done when: the `taken` line carries R and P, and the questions (or "no questions") are in
the plan file. R1 has no plan file: its `taken` line is the record.

## 2. Plan
- R1: no plan. R2: a short plan. R3: a full plan with a design section (D035).
- Write it from `references/plan.md` to `~/projects-days/<project>/<date>/<block>/plan.md`.
- Every plan has: done-when (checkable), assumptions, files, tests named with what they
  assert, tasks with who and model, the agents it uses, estimate, out of scope.
- The agents list is the block's agent budget (D006). Set it before the critic runs:
  `bedrock session set agent_budget=<n>`, where n is a whole number: every agent run the
  block needs in this 5-hour window, each critic round and review round counted.
- Research per `references/research.md` when the plan rests on library behaviour (D034).
- The project's packs feed the plan: their test checklists go into Tests, their rules into
  the implementer brief's "Keep true".

Done when: the plan file exists and its done-when is a test, a command or a number.

## 3. Critic
- R1: none. R2: one critic agent, one round. R3: two critics on different models, at most
  two rounds (D036). A second round with no fewer blockers goes to the owner.
- Brief from the plugin's `templates/briefs/brief.md`; give it the plan, done-when,
  decisions and code rules.
- Take each finding with evidence or drop it; a blocker is re-read in the code first.
- Tell the owner only the delta: "критик: 5 найдено, 3 принято, +20 мин".

Done when: the plan file has a "Critic" section with taken and dropped findings.

## 4. Owner's go
- R1: the request itself is the go.
- R2, R3: show the plan in five lines and wait for «го» (one go covers the whole plan, D016).
- Then `bedrock log plan-approved --block <id>`, and:
  ```
  bedrock session set task="<title>" plan='[0,<n>]' estimate_min=<m> state=work
  ```

Done when: the log line exists and the status line shows the task.

## 5. Cut into tasks
- One task = one commit with its own test, about 30–40 minutes of human work, its own files
  (D037). Add each with `bedrock backlog add '<json>'`.
- Set auto-continue for the first task:
  `bedrock session set autocontinue.next='{"id": "T1", "title": "...", "safe": true}'`.
  A task with an outward or destructive step is never `safe`: set `null` instead, so the
  session stops there and asks.

Done when: every task is in the backlog with files, test, who and estimate.

## 6. Implement each task
1. `bedrock backlog claim <id> --session "$CLAUDE_CODE_SESSION_ID"` (it sets `doing`).
2. Follow `references/implement.md` (D039): a failing test first, minimal code, verify after
   every few edits, refactor only while green, read the diff yourself, commit.
3. After the commit: `bedrock backlog status <id> done`,
   `bedrock log task-done --block <block> --ref <commit>`,
   `bedrock session set plan='[<k>,<n>]'`, and point `autocontinue.next` at the next task
   in order. It is `null` when none is left or the next one is not safe. Never skip over an
   unsafe task to a later one.

Done when: the task's test failed before and passes now, the commit exists, and the
backlog shows the task done.

## 7. Review
- Use the `review` skill for every block. It scales itself: R1 gets the checks and a
  quick read, R2 and R3 get both reviews (D050).
- The full suite runs once at the end of the block and before a PR: `bedrock cmd test`
  (D040).
- `bedrock log review --block <id> --detail "<the summary line>"`.

Done when: the review summary line is logged and `bedrock review pass <branch>` is recorded.

## 8. Deliver
Follow `references/deliver.md`: branch and PR per the project, live verification, and every
outward step only under the owner's grant (D052, D053). After a merge:
`bedrock log merged --block <id> --ref <PR>`.

Done when: the change is checked live, or the report says plainly that it was not, or it
names the outward step that waits for the owner's grant.

## 9. Close the block
- `bedrock log closed --block <id>` and `bedrock minutes <id>` into the report.
- Update the knowledge base for every module touched (the Stop hook asks once).
- Report to the owner in plain Russian (D021): what changed for the product, checked live
  or not, what is needed from the owner, what is next.
- `bedrock session set state=null task=null plan=null autocontinue=null agent_budget=null`.

Done when: the log line, the base update and the report are all done.

## End of day
`references/start-of-day.md` § End of day. Done when the owner has the day summary.
