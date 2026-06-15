# Bedrock — operating rules (how to use the skills)

> Shipped by the Bedrock template. These are the **universal** rules for driving the four skills.
> When you start a project, run **genesis** first. genesis adds your project's specifics in the
> **"Project rules"** section at the bottom — it never rewrites the universal rules above it.

## Which skill owns a request (route deterministically)

- **Start / plan a project, or re-plan after the spec changed (or a new feature is requested in a
  managed project)** → **genesis**.
- **Design or (re)build the visual layer of a web product** → **design-creator**.
- **Audit existing code for bugs / security / performance** → **code-review**.
- **A vague request no skill above clearly owns** ("fix this", "make it work", "разрули") →
  **prompt-refiner** — it sharpens and routes, and stays silent whenever another skill can start as-is.
- A small, already-clear task in no skill's domain → just do it.

## Gate mandates

- **Design** → design-creator. Pass **structured constraints only** (the design-brief) — never a
  hook, aesthetic, or narrative (it collapses the engine's output diversity).
- **Code audit** → code-review (review-only): the loop **implement → review → apply fixes →
  re-review**. **Scale to risk:** a trivial diff → light review; auth / money / migrations / crypto →
  full gate. Don't run a full audit on every 3-line change.
- **Residual execution** (non-design, non-audit) → the file-driven loop below.

## The file-driven loop (residual work)

1. `python3 .claude/skills/genesis/scripts/backlog.py --root . next` → the next ready task.
2. Do exactly **one** task — stay inside its `files`, satisfy its `acceptance`.
3. Run the matching gate, scaled to risk.
4. `backlog.py --root . done <id>` (or `status <id> <state>`).
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

## More

Full manual, every feature, edge cases: `.template/INSTRUCTIONS.en.md` / `.template/INSTRUCTIONS.ru.md`.
On-disk handoff surface across skills: `tools/INTER-SKILL-CONTRACT.md`.

---

<!-- GENESIS-PROJECT-RULES: genesis fills the section below on first run (read-and-extend; it never
     rewrites the universal rules above). Until then this is a placeholder. -->

## Project rules

_(empty — run **genesis** to populate this: it adds `@RULES.md` (your project's canon — stack, scope,
code style) and a one-line project summary here.)_
