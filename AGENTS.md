# Operating rules — how to use the Bedrock skills

> The **canonical** rules for this repository. Read by every coding agent that supports the
> `AGENTS.md` standard (Codex, Cursor, Roo, Windsurf, …). Claude Code reads it through `CLAUDE.md`
> (`@AGENTS.md`). genesis adds your project's specifics in the **"Project rules"** section at the
> bottom (inline) — it never rewrites the universal rules above it. Run **genesis** first when you
> start a project.

## Which skill owns a request (route deterministically)

- **Start / plan a project, or re-plan after the spec changed (or a new feature in a managed
  project)** → **genesis**.
- **Design or (re)build the visual layer of a web product** → **design-creator**.
- **Audit existing code for bugs / security / performance** → **code-review**.
- **A vague request no skill above clearly owns** ("fix this", "make it work", "разрули") →
  **prompt-refiner** — it sharpens and routes, and stays silent when another skill can start as-is.
- A small, already-clear task in no skill's domain → just do it.

## Gate mandates

- **Design** → design-creator. Pass **structured constraints only** (the design-brief) — never a
  hook, aesthetic, or narrative (it collapses the engine's output diversity).
- **Code audit** → code-review (review-only): the loop **implement → review → apply fixes →
  re-review**. **Scale to risk:** trivial diff → light review; auth / money / migrations / crypto →
  full gate.
- **Residual execution** (non-design, non-audit) → the file-driven loop below.

## The file-driven loop (residual work)

1. `python3 .claude/skills/genesis/scripts/backlog.py --root . next` → the next ready task.
2. Do exactly **one** task — stay inside its `files`, satisfy its `acceptance`.
3. Run the matching gate, scaled to risk.
4. `python3 .claude/skills/genesis/scripts/backlog.py --root . done <id>` (or `status <id> <state>`).
5. Re-read the invariants at the unit boundary, then loop.

## Status seam (enforced, not requested)

`genesis.tasks.json` is the single source of task **state**; `PLAN.md` is GENERATED. Change state
**only** via `backlog.py`. **Never hand-edit `genesis.tasks.json` or `PLAN.md`** — `backlog.py
validate` re-renders and diffs, so a hand-edit is a VISIBLE failure (non-zero exit), not silent drift.

## Map-read protocol

Before analyzing project structure: `python3 tools/project-map/build.py <root> --check`.
`fresh` → use it · `stale` → rebuild (`build.py <root>`) then use · `absent` / can't rebuild → say so
and limit analysis to files actually read. **Never serve a stale map as fact.** Edges and slices are
**leads to read** (open `file:line` and confirm), not facts. `--check` is cheaper than a build
(re-hashes, no parse; O(repo bytes)) but **not free** — don't call it in a hot loop. Full protocol +
schema: `tools/project-map/CONTRACT.md`.

## Source of truth (highest wins)

`docs/decisions.md` → `docs/architecture.md` → `docs/glossary.md` → `docs/open-questions.md`.
`project-context/` is history — **not** a source of truth (on conflict, the spec wins). **Never invent
a missing decision** — record it as `TODO(decision: …)` in `open-questions.md`.

## Machine contract (do not hand-edit — verified by `tools/drift-check.py` against `tools/contract.json`)

The gate mandates above cite these commands; drift-check parses the region below and confirms it
matches the contract and that each command is implemented:

<!-- @bedrock-contract
gate-commands:
  backlog.py next
  backlog.py done
  backlog.py status
  build.py --check
-->

## More

Full manual, every feature, edge cases: `.template/INSTRUCTIONS.en.md` / `.template/INSTRUCTIONS.ru.md`.
On-disk handoff surface across skills: `tools/INTER-SKILL-CONTRACT.md`.

---

<!-- GENESIS-PROJECT-RULES: genesis writes your project's rules below on first run (read-and-extend;
     it never rewrites the universal rules above). They live INLINE here — NOT behind an @import — so
     every agent (not just Claude) sees them. -->

## Project rules

_(empty — run **genesis** to populate this: it writes your project's canon — stack, scope, code
style — here, inline, plus a one-line project summary.)_
