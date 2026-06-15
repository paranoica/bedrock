# Inter-skill contract

The skills orchestrate through **files on disk**, not conversation. This document is the human-readable
map of that handoff surface.

The **machine source of truth for paths, commands, and anchor facts is [`contract.json`](./contract.json)**.
`tools/drift-check.py` validates that the skills, their scripts, and the canon all agree with it (and
`tools/run-evals.sh` / CI run it). This file **documents** the surface — it deliberately does **not**
re-list the concrete paths, because a second list is a second source that drifts (exactly the rot
drift-check exists to catch). When you need a path or command, read `contract.json`.

## Who writes / reads what

- **genesis** writes the project's source of truth — the spec (`docs/`), the backlog (`PLAN.md` +
  `genesis.tasks.json`), the canon (`AGENTS.md` — universal rules shipped, project rules filled
  **inline**) plus per-agent wrappers (`CLAUDE.md` = `@AGENTS.md`; others on demand), and the first
  project map. It mutates task state only through `backlog.py` (never by hand), and reads the map
  before analyzing structure.
- **Agent-agnostic canon:** `AGENTS.md` is the canonical rules doc — the cross-agent standard read
  natively by Cursor, Roo, Windsurf, and Codex. Other agents get thin wrappers (`CLAUDE.md` =
  `@AGENTS.md`; Aider one config line; Continue a generated rules file; **Antigravity** a
  `.agents/rules/bedrock.md` workspace rule that `@`-imports `AGENTS.md`). Catalog: genesis
  `references/agent-wrappers.md`.
- **The project map** is the shared structural index, built by `tools/project-map/build.py`. Freshness
  is stamped; consumers run `build.py --check` first and never serve a stale map as fact. Edges and
  domain slices are *leads to read, not facts*. Schema + protocol: `tools/project-map/CONTRACT.md`.
- **genesis → design-creator**: a closed, structured brief (`.genesis/design-brief.json`) — domain,
  audience, surfaces, in/out scope, tone, brand assets. **No hook or narrative** (that collapses the
  design engine's diversity). Consumed by the **agent invoking design-creator** (fed into dc's survey
  as known answers) — dc is vendored unchanged and has no autonomous reader for the file. See genesis
  `references/design-handoff.md`.
- **The review loop**: implement → **code-review** (review-only) → apply fixes → re-review, scaled to
  risk (trivial diff → light; auth/money/migrations → full).
- **prompt-refiner** activates **only on residue** — a request no other skill resolves. It sharpens
  the request and routes it; otherwise it stays silent.

## State: committed vs rebuildable

Committed (source of truth + history): `docs/`, `PLAN.md`, `genesis.tasks.json`, `AGENTS.md`,
`CLAUDE.md` (+ any per-agent wrappers), `project-context/`. Rebuildable / local (git-ignored):
`.map/`, `.genesis/`, `.refiner/`.
See `.gitignore` — the split is load-bearing (a committed stale map, or a lost backlog, both break the
"spec is the source of truth" invariant at the repo level).

## Keeping it honest

`tools/drift-check.py` fails (non-zero) when `AGENTS.md`'s machine-contract region, the map contract,
and genesis's scripts disagree on paths / commands / anchor facts — so the contract cannot rot across the
projects this template seeds. It reads its values from `contract.json` and from the real code
(`backlog.COMMANDS`, `anchors.CROSS_CUTTING`), so the checker itself can't drift from what it checks.
