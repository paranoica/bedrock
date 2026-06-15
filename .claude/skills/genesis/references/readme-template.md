# README template — the project's own README (genesis emits this at the repo root)

genesis writes a **short, project-facing** `README.md` at the repo root, parametrized from the spec.
It is for a human landing on *the project* — it is **not** the template's own docs (those live in
`.template/`, untouched).

## Overwrite rule (governance — never clobber a real README)

- If the root README is the **Bedrock stub** (it contains the marker `<!-- BEDROCK-TEMPLATE-STUB`) →
  **replace** it (it is a placeholder).
- If it is a real, human-written README → **read-and-extend**; surface conflicts, never overwrite.

## Template (parametrize `<…>` from the spec; keep it short — link to `docs/`, don't duplicate it)

```markdown
# <PROJECT>

<one line: what it is and for whom — from docs/decisions.md>

> Status: in development. Source of truth: `docs/`. Plan: `PLAN.md`. Rules: `AGENTS.md`.

## What it does
<2–4 bullets from the in-MVP scope>

## Getting started
<once there is code: install / run steps — filled in as the backlog delivers them>

## How this project is organised
- `docs/` — decisions, architecture, glossary, open questions (the spec; source of truth).
- `PLAN.md` — the task plan (generated; change task state via the backlog tool, not by hand).
- `AGENTS.md` / `CLAUDE.md` — the rules every coding session follows.
```
