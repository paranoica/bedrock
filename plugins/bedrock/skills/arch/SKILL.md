---
name: arch
description: Architecture review on request — hot spots, deepening and deletion candidates, boundary breaks, stale notes; the pick designed three ways. Use for "архитектурное ревью", "что упростить", "architecture review".
disable-model-invocation: true
---

# Architecture review

Runs only when the owner asks. The retro offers it every two weeks (D061).

## Triggers
- RU: «архитектурное ревью», «что упростить в проекте»
- EN: "architecture review", "what should we simplify"

## 1. Candidates
1. Hot spots: `bedrock arch hotspots --days 90`, files that change often and are large.
2. Deepening: a shallow module whose interface is as wide as its body.
3. Deletion: code with no callers (`bedrock map callers <symbol>`), dead flags, unused rules.
4. Boundary breaks: imports that cross a module's stated boundaries (its module note).
5. Stale notes: `bedrock kb drift` and notes long untouched.
Every candidate cites the file and line it rests on.
Done when: the list is in `~/projects-days/<project>/arch-<date>.md`.

## 2. The owner picks
Show the list, ranked, one line each with its cost and its gain. The owner picks one or more.
Done when: the pick is written in the file.

## 3. Three designs
For each pick, three ways to do it, from two models: the `architect` agent and the
`escalation` agent, each with a brief from `templates/briefs/brief.md`. Each
design: the mechanism, the interfaces, what it costs, what breaks, and why the rejected ones
lose.
Done when: the designs are in the file and the owner chose one.

## 4. Record and cut
The choice becomes a decision note (the `kb` skill), then backlog tasks at their risk level.
The results go to the chat. A PDF report only when the owner asks for one (the `doc` skill).
Done when: the decision note validates and the tasks are in the backlog.
