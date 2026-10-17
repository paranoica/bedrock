---
name: handoff
description: Shift handover — write a ten-section handoff note before a restart, or resume from one. Use for "пора рестартить", "передай смену", "продолжаем", "handoff", "resume".
---

# Handoff and resume

A fresh session with a handoff is the main way to carry work. Auto-compact is only a safety
net (D028).

## Triggers
- RU: «напиши хэндофф», «передай смену», «продолжаем»
- EN: "write a handoff", "hand over", "continue", "resume"

## When to write one
Write it early, without being asked, at any of these:
- a phase or block ends;
- a switch to another large task;
- before `/clear`;
- context reaches the early threshold, which the status line shows in yellow.

## 1. Write the note
1. Copy `templates/kb/handoff.md` to `~/projects-memory-bank/<project>/handoffs/<task>.md`.
2. Fill all ten sections. Each one is short and concrete:
   - **Role**: who the next session is for this task.
   - **Context**: five lines at most.
   - **Decided, do not reopen**: links to the decisions, `[[ACME-D12]]`.
   - **Hard constraints**: what must not change.
   - **Read, in order**: notes, files with line ranges, the plan.
   - **Task**: the next step, not the whole project.
   - **Done when**: a check with its command.
   - **Do not**: the tempting wrong moves.
   - **Traps**: what cost time in this session.
   - **Where the result goes**: files, notes, the backlog task id.
3. Put the decision notes it stands on into `stands_on:` in the frontmatter. A later decision
   then marks the handoff "re-check before use" (D026).
4. Link it from `handoffs.md`, then run `bedrock kb validate` and commit the store.
5. Test it: could a new session start without asking the owner anything? If not, it is
   unfinished. Fill the gap.
Done when: `bedrock kb validate` is clean and the store has no uncommitted changes.

## 2. Tell the owner
Two lines in Russian: «пора рестартить, хэндофф готов: <task>» and a proposed session name
(«имя сессии: acme-dedupe-search», D042). The owner runs `/clear` or opens a new chat, says
«продолжаем», and names the new session with `/rename`.
Done when: both lines are sent.

## 3. Resume («продолжаем»)
1. Find the work: the newest handoff in the project's `handoffs/`, the plan and the status
   note, `bedrock backlog list` for tasks in `doing` or `blocked`.
2. Read only the handoff and what it links. Never read old chats.
3. A handoff marked "re-check before use" by the validator: read the newer decisions,
   correct the handoff where they change it, and set its `updated` to today.
4. Baseline before any work: `git log --oneline -10`, `git status`, and the quick test
   command (`bedrock cmd test-related`, or `bedrock cmd test`). A red baseline is the first
   thing reported.
5. `bedrock log resumed --block <id>` and continue the task named in the handoff.
6. When the handoff's task is finished, set its `status: done`.
Done when: the baseline result and the next step are told to the owner in two lines.

## Pause and interruptions
- Task state lives in files: the plan, the status note, the day log. A pause needs no note.
- A call or an urgent task mid-way: `bedrock log paused --block <id>`, then
  `bedrock log resumed --block <id>` on return. The timer stops in between.
