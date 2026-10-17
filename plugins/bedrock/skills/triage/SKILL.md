---
name: triage
description: Bug triage — reproduce each report on the current version, group duplicates, set priority, decide fix, defer or decline. Use for "разбери баги", "что с репортами QA", "triage", "new bug reports".
---

# Bug triage

No report waits more than a day or two without a decision (D060).

## Triggers
- RU: «разбери баги», «что там QA прислали», «триаж»
- EN: "triage the bugs", "new QA reports", "what's in the bug queue"

## 0. Sources
The project's tracker where the team logs bugs, or whatever arrives: Slack, QA reports,
sheets. The project's settings name them. Reading is free. Writing to a tracker is an
outward action under the owner's grant (D016).
Done when: every source was read, or the one that could not be read is named.

## 1. Reproduce on the current version
For each report: the steps, expected (with its source), actual, on the current version.
Does not reproduce → say so, with what was tried. A report is never closed on a guess.
Done when: each report is marked reproduced, not reproduced, or needs information.

## 2. Group
Duplicates and shared causes go together; count them as k of n (D048). A cluster of
symptoms with one cause is one task.
Done when: the groups are listed with their report links.

## 3. Priority and decision
- Severity and reach give P0–P3 (D032). P0 goes to the urgent path of the `day` skill.
- One decision per group, stated with its reason:
  - fix now (into the backlog with its risk level);
  - defer, with why and until when;
  - decline, with why.
Done when: every group has a decision and the backlog holds the fixes.

## 4. Close the loop
- A report closes only after its original case no longer reproduces.
- The reply to the reporter is a draft for the owner, with what was done and how to check
  it. Nothing is sent by Claude (D044).
- Light pass daily with the inbox. Full pass on each new QA report.
Done when: the owner has one line, for example «баги: 7 новых, 2 дубля, 3 в работу (P1), 1
отложен до релиза, 1 не воспроизводится».
