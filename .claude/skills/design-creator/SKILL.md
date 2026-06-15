---
name: design-creator
version: 2.1.1
description: Universal web design engine for Claude Code. Use when the user runs the /design-creator command or explicitly asks to design, redesign, or build the visual layer of a website, landing page, dashboard, web app, or UI section. Produces distinctive, production-grade web design — typography, layout, motion, storytelling, 3D — that avoids generic AI aesthetics. Drives a three-stage pipeline (survey + mockup, optional scaffold, design-to-code) with quality gates. Not a project scaffolder by itself and not for non-web deliverables.
---

# Design Creator

A universal web design engine. It turns a design brief into distinctive, production-grade web design — and it is built to avoid generic "AI slop" output.

This skill is **methodology, not a project's design system**. It carries universal principles (how to choose color, how typography earns its "wow", how motion should behave). Project-specific values — exact tokens, stack, file-length limits, folder structure — live in the project's own `CLAUDE.md` and `.design/rules/`. This skill reads and respects those; it never hard-codes one project's specifics into itself.

## Activation

Trigger this skill **only** when:
- The user runs the `/design-creator` command, or
- The user explicitly asks to design/redesign/build the visual layer of a web product.

Claude **may suggest** running the engine ("this looks like a job for the design engine — want me to run `/design-creator`?") but must **never start it unannounced**. Routine code edits, copy tweaks, and non-visual work do not trigger it.

**Not this skill's trigger (hand to code-review instead).** A bare "review this / what do you think / проверь / посмотри код" on **existing** frontend code is a *review* request, not a design request — it belongs to the `code-review` skill (read-only, non-destructive), which will offer a design handoff if the issues turn out design-dominated. This engine triggers on intent to **design/redesign/build** the visual layer, not on intent to audit it. That one-line split is what keeps the two skills from both matching the same message.

## What this skill is and is not

- It **is** a design engine: it designs and implements the visual layer of web products.
- It **is not** a project scaffolder on its own. Raising a fresh frontend skeleton (package.json, routing, folder structure) is an **isolated phase** (Stage 2) that runs only when the user explicitly chose to build a new production project and no skeleton exists. The `bootstrap/` module is loaded only then.
- It **is not** for non-web deliverables (documents, slides, native mobile). Those have their own skills.

## The three-stage pipeline

The engine runs as a pipeline with **gates**. Each stage unlocks the next. The user is not obliged to pass all three — accepting a mockup and stopping is valid; a full new site runs all three.

```
Stage 1: Survey + Mockup   →  [GATE 1: user accepts the mockup]
   → bridge: design-token specification
Stage 2: Scaffold (optional, skipped if a frontend already exists)
Stage 3: Design-to-code  (with design-QA)
```

### Stage 1 — Survey + Mockup

1. Run the **survey** (see "The survey" below). Length scales to task complexity.
2. State the **design narrative in plain words** — the aesthetic family, the mode, the layout idea, key techniques, motion character. No code yet.
3. **STOP — confirmation gate.** Do not generate until the user approves the narrative — including the stated hook.
4. Generate the **mockup** as a standalone artifact in `.design/`. The mockup is visually accurate but rough in code terms — plain HTML/CSS, no production framework. It exists to be looked at and approved.
5. Mockup coverage: **main sections × {light, dark} themes × {desktop, tablet, mobile} breakpoints.** A partial mockup makes Gate 1 meaningless.
6. Iterate on user feedback — as many correction rounds as needed.

`.design/` handling:
- Stage 1 artifacts live in `.design/`. Bulky mockup iterations live in `.design/mockups/`.
- Gitignore **only** `.design/mockups/` (the heavy iterations). The token contract (`.design/tokens.json`), the decisions journal (`.design/journal.md`), and any committed design rules are NOT gitignored — they are the source of truth for Stage 3, design-QA, CI, and teammates. (See `index.json` → `gitignore_policy`.)
- If `.gitignore` does not exist, create it containing the line `.design/mockups/`. If it exists, append that line if absent. Never overwrite an existing `.gitignore` — append only.
- Keep a version history of mockups (`v1`, `v2`, …) so the user can roll back. **Never auto-delete versions** — offer cleanup to the user; deleting their rollback history silently is a governance violation (`governance.md`).
- Keep an episodic decisions journal at `.design/journal.md`: each significant choice with its *why* (hook, family, palette, perf budget, notable trade-offs). On a later session, read it to resume with rationale, not just values — so updates don't unknowingly undo past decisions. The journal is committed, not gitignored.

**GATE 1: the user explicitly accepts the mockup.** Nothing proceeds without this.

### Bridge — the design-token specification

When the mockup is accepted, extract a **specification document in real design-token form** (CSS custom properties: color ramp, spacing scale, type scale, radii, motion timings) plus the chosen aesthetic family, mode, and the list of techniques used. Stage 3 **consumes these tokens directly** — it does not re-interpret the mockup by eye. This document is also the reference target for design-QA.

### Stage 2 — Scaffold (optional)

Runs **only** when the user chose to build a new production project **and** no frontend skeleton exists. Skipped entirely when a frontend already exists.

Load `bootstrap/scaffold.md` and follow it. In short: build a modular frontend skeleton; read an existing `CLAUDE.md` and build to its rules, or — if none exists — ask for the key parameters (stack, structure, file-length limit, indentation) or take sensible stack defaults, then create `CLAUDE.md` in both the repo root and the frontend. The skill never bakes one project's concrete values into itself; it reads them or asks.

### Stage 3 — Design-to-code

Implement the design **on top of the existing skeleton**, driven by the token specification from the bridge. Use `principles/` (technique library) and `patterns/` (section recipes). Apply the per-technique status system and the active mode. Run design-QA (`principles/design-qa.md`) — including the binary check that the stated hook is actually realized.

### Stage 3.5 — Ship gate (code-review handoff)

When Stage 3 has produced **real code** (not a mockup-only stop), run an external safety pass
before final handoff to the user: spawn the **code-review** skill as an isolated review-only
subagent on the generated files (see `tools/handoff.md` for the exact contract). It catches
what design-QA can't — fatal/security bugs, dependency CVEs, removed defenses, deeper a11y and
performance issues. design-creator applies the fixes itself (or surfaces design trade-offs to
the user), then re-runs the design-QA gate on the fixed code. This is automatic and terminal:
the review returns findings and launches nothing back (loop guard in `tools/handoff.md`). If
the code-review skill isn't installed, say so once and ship without it — never block on a
missing companion.

## The work loop (inside a generation stage)

For each section / screen / component:

1. **Survey** — gather inputs (adaptive; see below).
2. **Narrative in words** — describe the intent. The narrative MUST include an explicit line stating **the hook** of this site (see `principles/concept.md`) — the one central idea the page is built around.
3. **STOP — confirm the intent** with the user. (For tiny edits this step may be skipped — see "Scaling to task size".)
4. **Generate** — write the code, following `principles/`, `patterns/`, statuses, and mode. Lock the **decisions** (tokens: palette, type scale, one accent, archetype, signature) before coding and transcribe them — but keep the generation prompt to yourself *lean* (a rich prose template collapses diversity; constrain the tokens, not the wording). See **Making the first try land** below for diverse-candidate sampling, adaptive N, and the cold-start pick. **Lock a contrast-safe palette FIRST (layer 1):** run `node tools/contrast.mjs check .design/tokens.json` (or `contrast.mjs pair <fg> <bg>`) and fix any pair under the AA floor *before* coding — contrast is computed here, not eyeballed and discovered by axe at the gate.
4b. **Self-revise against the render (layer 2) — before the gate/critic.** Render your own output (`tools/verify.mjs`) and **LOOK at your own screenshots**: fix what only the pixels reveal — position, size, transparency/layering, optical balance, collisions/overlap at each breakpoint. Re-render and repeat until stable. This is the generator cleaning its own spatial defects; it is the engine's job, not the owner's. (Layer-3 taste calls are NOT fixed here — they go to the owner.)
5. **Self-check (design-QA) — the QA GATE.** Run the full blocking checklist in `principles/design-qa.md`. Every check is binary; any "no" blocks progress. Then **spawn the independent critic** (`tools/critic.md`) on the result — on **every** result, one section or more — via `Task(subagent_type: "general-purpose", prompt: <contents of tools/critic.md> + the inputs it lists: build path, `.design/tokens.json`, `.design/verify/verify-report.json`, the stated hook, deliverable type, mode, and the matching `references/` exemplar)`. It re-checks the work in a fresh context it didn't generate, so it can't be anchored by your reasoning. Treat its `FAIL`s as authoritative; fix defects silently and re-run (self-check + critic) until both are green. This is mandatory and automatic — Claude does not skip it, defer it, or ask permission. (No install needed — the critic is spawned from the bundled file, not registered in `~/.claude/agents/`. If a user *has* registered a `design-critic` agent, delegating to it by name is equivalent.) **The critic *step* is mandatory; its *mechanism* tiers by host capability:** Tier A — fresh-context `Task` subagent (preferred); Tier B — a registered `design-critic` agent; Tier C — a single-context self-critique run explicitly against `tools/critic.md` and the exemplar, **labelled lower-assurance** in what you show the owner. State which tier ran; never show the gate green on a skipped critic.
6. **STOP — show the result** to the user. This step is physically blocked until the step-5 gate is fully green — an unfinished result is never shown.
7. **Branch on feedback** — edits needed → back to step 4; accepted → next section. **Close the critic loop:** once the owner resolves what the critic SHIPped, log it with `node tools/calibration.mjs record-critic <SHIP|FIX_AND_RERUN> <1 if owner kept it else 0> --tier <A|B|C>`. This is the design-side analogue of the review skill's Brier loop — over time `calibration.mjs report --kind critic` tells you whether critic-SHIP actually predicts owner-keep; if it keeps underperforming, the critic is too lenient and its bar rises. Without this the critic asserts PASS/FAIL but never learns.
8. Section done.

Claude stops **exactly twice** per loop: to confirm the intent and to show the result. Everything else — generation, the QA gate, fixing defects — it carries by itself. The QA gate (step 5) is automatic and blocking: the result is never shown until it is fully green. A deeper full-page audit may additionally be offered, but never replaces the per-step gate.

## Fix ownership — three layers (the owner only arbitrates taste)

Every defect belongs to a layer, and **only the last reaches the owner.** Surfacing a layer-1 or
layer-2 defect to the owner as *their* problem is itself a defect — the engine owns both.

- **Layer 1 — the measurable floor (engine owns; fixed silently in-loop; never surfaced).**
  Contrast (`tools/contrast.mjs` at token-lock + axe in `verify.mjs`), 320px overflow, off-scale
  spacing/type, CLS, reduced-motion compliance, scroll/3D jank. These are **computed/measured, not
  judged** — the owner never hand-fixes them. (This is the class the gallery showed failing 14/15
  when the loop was skipped — exactly what must not happen.)
- **Layer 2 — render-time spatial defects (engine owns; the step-4b self-revision loop).**
  Position, size, transparency/layering, optical balance, collisions/overlap. Not preventable
  blind — the engine renders, *looks at its own screenshots*, and fixes before the critic.
- **Layer 3 — taste (the only thing brought to the owner).** The hook/direction, family/mode, the
  final "do you like it", and the irreducible nudges that are judgment, not bugs.

The whole pipeline is built so the owner spends attention on layer 3 and is never made the QA
department for layers 1–2. Ambition stays high *because* the floor and the spatial cleanup are the
engine's job, not paid for by dialing the design down.

## The survey

The survey is an **adaptive tree**, not a fixed list. **Survey length = task complexity.** A tiny fix is 1–2 questions; a complex new project with 3D can be 30+. Every question must earn its place — it clarifies something Claude would otherwise invent. Branches that do not apply are skipped entirely. Questions may also surface later, in context, when a specific section is reached — the engine asks *in time*, it does not dump 50 questions as a wall.

**Skeleton of the tree:**

- **Q0 — Task type** (entry fork):
  - *Mockup / concept* → artifact in `.design/`, full survey, no project code touched.
  - *New project* → full pipeline (survey → mockup → scaffold → design).
  - *Edit existing* → **fast path**, bypassing the long survey. One sub-question — scope assessment: a small thing (fix a component) → do it directly, no fuss, briefly; something large (rebuild a landing page) → propose options first, then change without overreach.
- **Q1 — Aesthetic family**: editorial · cinematic dark · warm · terminal · playful · glass · data-dense · neon-brutalist, etc. Sets *character*.
- **Q2 — Mode — Clean or Statement**: sets *intensity* across all blocks at once.
- **Q3 — Density** (airy / dense) + layout width + themes (two themes by default).
- **Q4 — 3D needed?** (fork): *no* → the whole 3D branch is skipped. *Yes* → level, material, asset source.

Around these nodes, add as many refining questions as the task needs (project context, audience, the site's job, references the user likes, brand assets, content availability, section/page count, technical stack if a new project). The tree is the **scaffold of survey phases**; the real question count floats.

**The page archetype.** Alongside the hook, the engine consciously picks a **page archetype** from `principles/page-architecture.md` - never defaulting to the classic nav->hero->strip->grid->cta skeleton. Across multiple projects it must vary the archetype.

**The hook.** After the aesthetic family (Q1) and mode (Q2) are set, the engine works out **the hook** — one bold, specific central idea for this site (see `principles/concept.md`). This is mandatory; it is not a survey question the user answers but a concept the engine forms from the project context and states for approval.

**End of survey:** state the narrative in words (including the hook) → confirmation → generation.

**Golden default:** if the user says "just do what's best, don't grind me with questions", proceed on a sensible default — Clean mode, editorial family, two themes, baseline motion — but always still extract the minimum answers needed; the engine never works on zero input.

## Making the first try land (generation discipline)

Gates catch slop after the fact; if the generator samples from the median, the gates just
force endless regeneration. Most of "ahuenny on the first try" is won *before* the first token,
by moving the distribution — not by filtering. Four moves, each grounded:

1. **Shift the mean (kill typicality).** Slop is mode collapse toward the *typical*. Counter it:
   (a) **reference-condition** — `reference-scout.md` pulls 3–5 current award-tier exemplars of
   the chosen family and you generate by transposing their *technique/structure DNA* onto this
   content (retrieve on similarity **and** diversity, not five near-clones); (b) **Verbalized
   Sampling at the hook stage** (see `concept.md`) — ask for several candidate hooks/directions
   *with* their likelihoods and pick from the interesting tail, never the single most-probable
   (that one is the median); (c) **taste-prior** — feed the owner's past *winners* (from
   `memory.md` / `tools/taste.mjs`) as in-context exemplars so the bias is toward what *this*
   owner keeps.
2. **Cut the variance (kill the slop tail).** The MUSTHAVE-BASE hard bans (`anti-slop.md`) are
   negative-prompting — they chop the tail. Lock the token/technique decisions before coding so
   codegen is transcription, not invention. **But do not over-template the prose** — a rigid
   30-point prompt mold collapses the diversity move 1 just bought. Lock decisions, keep wording
   lean.
3. **Hedge the residual (diverse best-of-N).** On a subjective axis a single sample is a die
   roll. For an expressive brief, generate a **small set of deliberately *different* candidates**
   (different archetype/hook/mechanism — not N tweaks of one) and let the critic pick via
   **pairwise-vs-anchor** (not absolute scoring — the aesthetic judge is weak at absolute, see
   `tools/critic.md`). **Make the spread mechanical, not hoped-for:** run `node tools/spread.mjs
   assign <brief> <N>` to get N distinct archetype\u00d7mechanism cells (tail-biased, avoiding the
   last-K used per `.design/ledger.json`), generate **each candidate into its assigned cell**, and
   on the winner `spread.mjs commit <archetype> <mechanism> --family <F>` (logs the cell + novelty
   percentile). `spread.mjs check` returns **REROLL** on an unpinned exact-cell repeat — honor it.
   See `principles/diversity.md`. Scale N to stakes (**adaptive**): N\u22483 for a flagship landing,
   N=1 with strong reference-conditioning for an ordinary section. **Weak-batch guard:** if every
   candidate is below the median-anchor, do **not** ship the least-bad — regenerate or escalate;
   best-of-N returns garbage when the whole batch is garbage.
4. **Cold-start (no taste history yet).** First project for a new owner has no winners to bias
   toward, so "likely *this* owner likes it" defaults to "likely the median likes it". Collapse
   the space *before* generating: show **2–3 micro-direction options** (family×mode thumbnails)
   and let them pick one — pairwise picking provably beats cold-start. The engine already
   surfaces a few final-design variations; the cold-start pick is the same move pulled to the
   *front*, on directions instead of finished pages.

These interlock with the gates (`critic.md`) and the taste loop (`memory.md`, `tools/taste.mjs`,
`tools/tournament.mjs`): owner pairwise votes feed one taste model whose winners become
generator exemplars (move 1c), critic anchors (move 3), and eval-tournament champions.

## Scaling to task size

The engine scales depth to the request:
- Everything already exists, small change needed → quick, sharp analysis → if small (tweak a component) just do it, briefly, no fuss; if large (rebuild a landing) propose options, then execute.
- Skeleton exists, no code → run the mockup, then build with corrections.
- Nothing exists, full site needed → full pipeline.

Volume per run is situational: asked for a site, it does the whole site; asked for a section, just the section. For large volume the engine may **spawn sub-agents to work in parallel** (one on the landing, one on the dashboard) — but only **under a lead-planner**: the planner holds the shared token contract (`.design/tokens.json`) as a lock, assigns scopes, and runs a reconciliation pass at the end to resolve conflicts (divergent micro-interactions, drifted token interpretations, repeated hook-mechanisms). Independent agents with no shared state are forbidden — that reintroduces exactly the cross-surface fragmentation the engine exists to prevent. Coherence is the planner's job; parallelism is just how the work is divided under it.

When an asset is missing that Claude genuinely cannot produce (a specific 3D model, a complex illustration): by default place a **placeholder marked "asset needed"** and continue the rest of the work; afterwards, return and offer the user options (AI generator / stock / artist). Do not block the pipeline.

## Two axes: aesthetic family × mode

Design is set on **two independent axes**:
- **Aesthetic family** (Q1) — the character (editorial, cinematic dark, terminal, warm, playful, glass, data-dense, neon-brutalist…).
- **Mode** (Q2) — the intensity (Clean / Statement).

They are orthogonal: "cinematic dark in Clean" and "cinematic dark in Statement" are both valid. See `principles/aesthetic-families.md` and `principles/modes.md`.

## The technique status system

Every technique in `principles/` carries a **status — the status IS the instruction.** Claude reads the status and knows what to do without guessing. The five statuses:

- **MUSTHAVE-BASE** — always, non-negotiable. Two kinds live here. (a) Technical hygiene / correctness: `:focus-visible`, `object-fit: cover`, skeletons for async, smooth overlay open/close, `prefers-reduced-motion`. (b) Hard anti-slop prohibitions (aesthetic, not correctness — but equally non-negotiable): no emoji, no Inter/Roboto as display voice, no purple-as-default, no AI status-badge. Both cannot be overridden — disabling them is a defect, not a choice.
- **MUSTHAVE-DEFAULT** — applied by default, overridable by an explicit user request or a stated concept. Examples: list stagger cascade, number counter animation, link underline-slide. Claude applies them immediately and removes them only when the user says so.
- **SITUATIONAL** — not applied until proposed in the survey and approved by the user.
- **STATEMENT** — available only when mode = Statement; blocked in Clean.
- **DROPPED** — never applied. Recorded as an explicit prohibition with a reason, so Claude does not "re-discover" a popular technique on its own.

**Cross-cutting rules** sit above all statuses and always apply: `prefers-reduced-motion`, mobile fallbacks for heavy/cursor-dependent effects, animate only `transform`/`opacity` (60fps), no emoji, **intensity-by-hierarchy** (every element has its own ceiling — a hero is rich, an ordinary section is calmer).

## The mode mechanic

Mode is a **filter over statuses**, not a separate body of text. One switch changes what is active across every `principles/` file at once:
- **Clean** — MUSTHAVE-BASE, MUSTHAVE-DEFAULT, SITUATIONAL active; STATEMENT techniques blocked.
- **Statement** — everything above plus STATEMENT techniques unlocked (still dosed by hierarchy).

Mode is a strong default, not a cage: the user may request a single Statement technique inside a Clean project, and Claude does it (an explicit override). Finer nuance comes from the family × hierarchy × point overrides, not from adding more modes.

## File map

- `index.json` — the router + state map. Read first. Tells you which files a task needs (lazy load) and where durable state lives.
- `SKILL.md` — this file. Orchestrates the pipeline, holds the gates, decides whether Stage 2 is needed.
- `principles/` — the research, split by block. The technique library. Used in Stage 1 and Stage 3.
  - `invariants.md` — the compact non-negotiable core; re-read before every step and gate (reinjection).
  - `anti-slop.md` — what NOT to do; read first, always.
  - `ambition.md` — the courage floor: ambitious by default, justify down not up, timidity is a defect equal to slop.
  - `concept.md` — the hook: the one central idea each site is built around; read right after anti-slop.
  - `reference-scout.md` — stock imagination from the live web
  - `frontend-gotchas.md` — hard-won render-time failure modes (containing-block trap that breaks
    modals under animated scroll, backdrop-filter jitter, icon flicker, end-of-animation jitter,
    rounded-clip AA seam, smooth-scroll-vs-INP) and how to prevent them by construction. (Awwwards/Codrops/studio sites + the user's `.design/refs/`); extract technique & structure, never assets/code; feeds the hook.
  - `governance.md` — what the engine never does silently (destroy work, fabricate content, pass guesses as fact); conflict arbitration order.
  - `memory.md` — owner taste profile (two-level, advisory) and the sameness ledger (soft repeat-flag + favorites pin).
  - `seo.md` — technical + structural SEO/GEO (head, schema, SSR, CWV, semantics); for public-facing pages.
  - `interaction-detail.md` — the micro-level: how every icon, button, card, link is finished so nothing ships half-done.
  - `color.md`, `typography.md`, `layout.md`, `composition.md`, `depth.md`, `optical.md`, `signature.md`, `storytelling.md`, `motion.md`, `icon-morphing.md`, `skeletons.md`, `micro-mechanics.md`, `responsive.md`, `optimization.md`, `perf-budget.md`, `frontend-safety.md`, `design-qa.md`, `3d.md`, `decorative-graphics.md`, `kinetic-type.md`, `forms.md`, `screen-states.md`, `photography.md`, `cursor.md`, `data-viz.md`, `theming.md`, `accessibility.md`, `aesthetic-families.md`, `modes.md`.
- `patterns/` — section recipes (anatomy, not clones). One file per section type.
- `tools/` — operational modules. `handoff.md` — the design-creator ⇄ code-review cross-skill contract (ship-gate + loop guard). `verify.md` + the **bundled `verify.mjs`** (real Playwright+axe runner) — the render+screenshot+axe+CWV+**motion** verification that backs the QA gate, emitting a hash-bound report the gate reads instead of self-attesting. The motion pass drives a scripted scroll and measures non-inert hook, scroll-jank, reduced-motion compliance, and (for a webgl canvas) the 3D budget — turning those from Tier-3 judgment into Tier-1 measured. Its regression is `evals/motion.mjs` (render-backed, self-skips without a browser). `contrast.mjs` — the render-free WCAG contrast pre-check over `.design/tokens.json` (the layer-1 floor, computed at token-lock — fixes a sub-floor palette before axe ever catches it at render); `node tools/contrast.mjs selftest` guards the math (CI-safe, zero-dep). `ambition-check.md` — the grounded procedure that turns "gallery-tier?" from a vibe into proxies + pairwise + fresh-context agreement + calibration (`calibration.mjs`). `critic.md` — the independent fresh-context critic spawned at the QA gate on every result (Task subagent, no install) that cross-checks the work against the spec and returns authoritative PASS/FAIL. `preflight.mjs` — probes the QA toolchain at session start and derives `qa_mode`. `taste.mjs` — turns owner pairwise picks into an Elo taste model whose winners become generator exemplars + critic anchors. `tournament.mjs` — the eval Elo tournament with a regression guard (a rule change must beat the prior champion, not just differ). `spread.mjs` — the axis-spread + sameness-ledger enforcement that assigns each best-of-N candidate a distinct archetype×mechanism cell and rerolls unpinned exact-cell repeats (`principles/diversity.md`); `evals/diversity.mjs` measures whether outputs actually spread. `drift.mjs` — keeps the 35+ `principles/` surface in sync: flags principle files missing from the router and principles still pinned to an older `anti-slop.md` hash (run `node tools/drift.mjs check` after any anti-slop edit; advisory, never auto-edits).
- `evals/` — golden briefs + rubric to catch regressions after edits (run after changing any MUSTHAVE rule, the gate, or the invariants).
- `bootstrap/` — the scaffold module (Stage 2) and `adopt.md` (read an existing frontend's de-facto tokens to conform to it).
- `references/` — our own reference builds (Clean / Statement exemplars), safe to learn from; `inspiration.md` is the owner-curated reference pack the scout reads.

## Working language

The contents of this skill's files are in **English** (per the standard that skill instructions are English). The survey Claude runs **with the user at runtime** is in the **user's language**.

## Reading order at runtime

0. **Preflight (run ONCE):** `node tools/preflight.mjs` reports the QA toolchain (`playwright`/browser/`axe`) and derives `qa_mode` (`measured` | `requires-render`). Announce it up front in one line so the gate's teeth are known before generation, not mid-loop (requires-render ⇒ axe/CWV checks ship labelled, never auto-green; surface `npx playwright install chromium`). It also reports `tells.status` — if `stale` (`principles/tells-current.md` older than its 30-day interval), **propose** a tells-refresh (reference-scout pass → reviewable add/retire diff with provenance; never auto-edit).
0a. Read `index.json` (the router) and `principles/invariants.md` FIRST, every session. The router tells you which files this task needs (lazy loading — do not pull every principle in). The invariants are re-read before each generation step and at every QA gate (reinjection — fights context rot in long sessions).
1. Always read `principles/anti-slop.md` and `principles/ambition.md` (the two floors — against *bad* and against *forgettable*), then `principles/concept.md`.
1b. On an expressive brief (brand/marketing/portfolio/launch), run `principles/reference-scout.md` before fixing the hook — pull current technique/structure from the live web and the user's `.design/refs/`.
2. Read `principles/modes.md` and `principles/aesthetic-families.md` to set the two axes (and run the domain-fit guard).
3. Pull the `principles/` files the router lists for the current task — always including `interaction-detail.md`, `design-qa.md`, and `tools/verify.md` before any generation step, since the QA gate is mandatory. It is **measured when a browser is available** (`qa_mode: measured`); without one (`qa_mode: requires-render`) the render/axe/CWV checks ship **labelled unverified, never auto-green** — the gate still runs (critic + visual judgement), it just states which checks it could not measure.
4. Pull the `patterns/` file for the section being built.
5. For 3D tasks, read `principles/3d.md`.
6. For a new-project scaffold, read `bootstrap/scaffold.md`. For an existing frontend, read `bootstrap/adopt.md`.
7. For any public-facing page, read `principles/seo.md`. Read `principles/governance.md` whenever an action could touch the user's files or content.
