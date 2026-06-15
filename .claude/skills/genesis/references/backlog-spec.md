# Backlog spec — `genesis.tasks.json` schema + the rules

The backlog is `genesis.tasks.json` (the machine source of task **state**) rendered to `PLAN.md` (the
human view). State changes **only** through `scripts/backlog.py` — never hand-edit either file
(`backlog.py validate` re-renders and diffs, so a hand-edit is a *visible* failure, not silent drift).
Spec-ref hashes are stamped by `backlog.py stamp` via `scripts/anchors.py` — never hand-written.

## Task schema

```jsonc
{
  "id": "T012",                       // stable id (renaming is a structural change)
  "title": "...",
  "sprint": "S2",
  "status": "todo|doing|done|stale|needs-review|blocked",
  "dependencies": ["T004"],           // DAG edges; validated for cycles by backlog.py validate
  "spec_refs": {                      // the SINGLE task→spec link — its KEYS are the trace, the
    "decision:money-custody": "<h>",  // values are anchor hashes (forward closure, stamped by backlog.py)
    "term:escrow": "<h>"
  },
  "external_refs": ["ticket:JIRA-123"],            // optional; only NON-anchored refs (no overlap with spec_refs)
  "acceptance": [                                  // EARS array (≥1)
    "WHEN <condition> THEN the system SHALL <observable behavior>"
  ],
  "verify": { "kind": "test|manual|none", "handle": "<command or description>" },
  "files": ["api/payments/*"],        // self-contained: where to do the work
  "effort": "S|M|L",                  // OPTIONAL advisory only — NEVER gates decomposition depth
  "subtasks": [ ]
}
```

## Rules (see `invariants.md`, `anchor-contract.md`)

- **Re-derivable, not frozen.** On a spec change: content drift on a traced anchor → `needs-review`
  (soft); structural change (anchor removed/renamed) → `stale` (re-derive it); `done` is preserved (a
  drifted `done` → `needs-review`, never silently un-done). Run via `backlog.py re-derive`.
- **Decomposition cap = verifiability** (not subjective size): two subtasks may not be split unless
  each can be given a **distinguishable** `verify` handle + `acceptance`. `effort` is advisory only.
- **Self-contained.** Every task carries its `acceptance` (EARS), `verify`, `files`, and `spec_refs`,
  so it can be executed in a fresh context.
- **Open decisions stay wired.** A task whose `spec_refs` include an open `TODO(decision:)` anchor is
  flagged by `analyze_spec` as resting on an unresolved decision — not execution-ready until resolved.

## Commands

`backlog.py stamp | re-derive [--apply] | next | start <id> | done <id> | status <id> <state> [--note] | validate | render`
(all take `--root <dir>`; see the file-driven loop in `canon-template.md`.)
