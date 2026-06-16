---
name: genesis
version: 0.1.0
description: Project inception + (re)planning orchestrator. Use when the user wants to START or BUILD a new project, set up the spec and task backlog for a codebase that has none, or RE-DERIVE the plan after the spec changed — including broad/unclear "I want to build X" openers and Russian cues like "хочу сделать", "начать проект", "запланируй", "распиши задачи". Runs an adaptive interview (depth scales to complexity), then writes canonical spec docs (decisions/architecture/glossary/open-questions), a re-derivable task backlog (genesis.tasks.json + PLAN.md), the project's canon rules (AGENTS.md + a CLAUDE.md wrapper), and the first project map. It never invents missing decisions — it records them as open questions. NOT for reviewing existing code (that is code-review) and NOT for designing the visual layer (that is design-creator); genesis hands design-creator structured scope constraints only, never a hook or narrative.
---

# Genesis

The front door. Turns "I want to build X" into a grounded, source-of-truth spec, a re-derivable
task backlog, the project's canon rules, and a first structural map — so every later change runs
through the right gate. **Methodology, parametrized per project**: it never bakes one project's
concrete choices (stack, file-length, naming) into itself — it asks or derives them.

> **Status: complete.** Interview + generation core, the anchor/backlog scripts, canon-template,
> design-handoff, modes, the spec-verifier subagent, preflight, calibration, the CI emitter, and the
> seam + parametricity evals are all in place. `AGENTS.md` is the canonical cross-agent rules doc;
> per-agent wrappers (`CLAUDE.md` and others) are emitted per `references/agent-wrappers.md`. The
> router (`index.json`) maps every file.

## Read this first, every run
1. **`index.json`** — the router + state map. Read before anything else.
2. **`references/invariants.md`** — the compact non-negotiable core. Re-read at each phase
   boundary, before writing any spec doc, and at the top of the spec-analyze gate (reinjection).
3. **`references/anchor-contract.md`** — the one source for anchor grammar, the normalizer, the
   hash, and the reference graph. The generator and the gate share it; never fork it.

## Activation boundary

genesis owns **project inception and (re)planning**: "build X / start a project / unclear-broad at
project scale / re-plan the backlog", and **adopt** of a repo that has no canon or map. It does
**not**:
- review/audit existing code for bugs → that is **code-review** (read-only).
- design or build the visual layer → that is **design-creator**. genesis passes it a **design-brief
  of structured constraints only** (domain, audience, surfaces/page list, in/out scope, tone, brand
  assets) — **never a hook or narrative** (that collapses the design engine's output diversity).

A small, already-scoped task inside an existing project is not genesis (no intent to start/plan).
The residue between all skills belongs to **prompt-refiner**.

## Modes (read the mode file in `modes/`, then return here)

| Mode | When | What it does |
|------|------|--------------|
| **greenfield** | empty / near-empty repo; "start a project" | full pipeline below |
| **adopt** | existing repo with no canon/spec/map | reverse a skeletal spec + generate canon + first map; reads-and-extends any `CLAUDE.md`; **does not review code**. Observed facts cite file:line; inferred rationale → open-questions as `inferred/unconfirmed`, never asserted as decisions |
| **replan** | the spec changed, or new work is requested (e.g. routed from prompt-refiner) | on new work, amend the spec first (targeted interview on the delta → anchor it), then re-derive the backlog from the changed anchors, preserving `done` |

## Pipeline (with two stops)

```
0  Preflight (once)        → announce mode: full | degraded (git? python3? design-creator/code-review installed?)
1  Adaptive interview      → references/interview-taxonomy.md   [STOP: confirm interview coverage]
2  Canonical spec → docs/  → decisions · architecture(+data-model) · glossary · open-questions (all ANCHORED)
                             [STOP: confirm the spec narrative]
3  Derive backlog          → genesis.tasks.json (+ PLAN.md rendered); hashes stamped by backlog.py
4  Project rules + wrappers + README → fill AGENTS.md's "Project rules" section INLINE (this project's
                             canon: stack/scope/style; never rewrite the universal rules) + emit
                             per-agent wrappers for the agents selected in the interview
                             (references/agent-wrappers.md; CLAUDE.md=@AGENTS.md ships already) + the
                             project README.md (replace the Bedrock stub) + .github/workflows/ci.yml
                             (stack × project-type) + .github/workflows/spec-gate.yml (the gate in CI)
                             + a "Wire up CI" backlog task + .gitignore (compose common + stack +
                             bedrock block). See references/canon-template.md + readme-template.md +
                             ci-emit.md + gitignore-emit.md
5  First project-map       → tools/project-map/build.py → .map/project.json
6  spec-analyze gate       → deterministic checks + fresh-context spec-verifier + hash receipt (BLOCKING)
7  Archive + handoff       → project-context/ (raw + summary; NOT source of truth); design-brief if visual work follows
```

genesis stops **exactly twice** (confirm interview coverage; confirm the spec). Everything else —
generation, the gate, archiving — it carries itself. Step 6 is automatic and blocking: never
declare the spec/backlog ready on a skipped gate.

## Working language

This skill's files are **English** (per the skill standard). The interview genesis runs **with the
user at runtime** is in the **user's language**.

## What genesis does NOT do
- Does not review code (→ code-review) or design UI (→ design-creator).
- Does not invent missing decisions (→ `open-questions.md` / `TODO(decision:)`).
- Does not overwrite a `CLAUDE.md` or any user file — reads and extends, surfaces conflicts.
- Does not hand-write spec-ref hashes or hand-edit `genesis.tasks.json` / `PLAN.md` — those go
  through `scripts/anchors.py` / `scripts/backlog.py`.
