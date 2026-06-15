# Bedrock — overview (EN)

Bedrock is a GitHub **template repository** for starting software projects with high-quality,
AI-assisted output from day one. You clone it, describe what you want to build, and a small set of
cooperating **agent skills** sets up your spec, your task plan, and the rules every change follows —
then keeps the work flowing through the right quality gate. The **skills run in Claude Code**; the
**project they produce** is agent-agnostic — its rules live in the cross-agent **`AGENTS.md`**, so
Cursor, Codex, Windsurf, and more work under the same canon afterwards.

## What you get

- **genesis** — interviews you and writes the project's *source of truth*: decisions, architecture,
  glossary, and open questions (`docs/`), a re-derivable task plan (`PLAN.md` + `genesis.tasks.json`),
  the project rules (`AGENTS.md`, the cross-agent canon, plus a thin `CLAUDE.md` wrapper), a first
  structural map of the codebase, and a real, working CI workflow (`.github/workflows/`).
- **prompt-refiner** — quietly turns a vague request ("fix this", "make it work") into a precise,
  routed one — but only when no other skill already owns it.
- **design-creator** — designs and builds distinctive web UI, engineered to avoid generic "AI slop".
- **code-review** — a hard security / correctness / performance reviewer for existing code.

## Why it's different (the advantages)

- **The spec is the source of truth, and the plan re-derives from it.** Change a decision and the
  affected tasks are flagged automatically — the plan is never a frozen one-shot you hand-patch.
- **It never invents missing decisions.** Anything you haven't decided is recorded as an open
  question, not guessed — so the spec doesn't quietly contain fiction.
- **Nothing lies silently.** The code map carries a freshness stamp (a stale map is never served as
  fact); the spec↔task link is hash-checked; the skills' own contracts are drift-checked in CI.
- **The right tool runs automatically.** Design → design-creator; audit existing code → code-review;
  everything else → a simple loop over your plan. You talk; the files stay in sync.
- **Agent-agnostic by construction.** The rules live in `AGENTS.md` — the cross-agent standard read
  natively by Cursor, Codex, Roo, and Windsurf; Claude Code reads it via a thin wrapper. One canon,
  every agent (Antigravity via a `.agents/rules` import).
- **Honest, agent-friendly, and inspectable.** Everything is plain files at documented paths, and the
  quality gates have teeth — they *fail* (non-zero), they don't merely warn.

## Start

Run `/genesis` in Claude Code and say what you want to build (the resulting project then works with
any AGENTS.md-aware agent). For every feature, how each part works, and the edge cases, read
**[INSTRUCTIONS.en.md](INSTRUCTIONS.en.md)**.
