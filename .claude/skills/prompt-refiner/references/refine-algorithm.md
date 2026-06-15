# Refine algorithm — what refiner does once it has TAKEN a residue request

Reached only after the residue-gate returned **residue** (`residue-gate.md`). The job: turn vague
residue into a precise, routed prompt — silently — and hand it to the engine it now resolves to (or
to direct execution). Refiner does not do the engine's work; it sharpens and routes.

## 1. Discover before you ask (difficulty-gated)

Default to **act + discover via tools**, not to questioning. Read the repo, locate the target, find
the file/symbol — most "what does this mean?" is answered by cheap exploration, not by the user.
Ask a clarifying question **only** when interpretations diverge into **materially different or
irreversible** work that exploration cannot settle — and then **at most one**, tight. (This is the
ask-vs-act calibration: over-asking is the failure mode.)

> Branch hygiene: the ≤1 question happens **after** taking. It is not the yield decision. Never both.

## 2. Sharpen into the CC-prompt schema (the output target)

A precise prompt for Claude Code contains, in order:
1. **One task, one verifiable outcome** (split multi-task mush; a multi-task prompt produces
   "almost works").
2. **Explicit file paths** (front-loaded — discovered in step 1, not guessed).
3. **Acceptance criteria** (what "done" means; testable).
4. **A verification handle** Claude can run itself (a test command, a build, a measurable target).
5. **A reference pattern** ("follow the batched-query pattern in `api/orders/queries.py`").
6. For bugs: **symptom + likely location + definition-of-fixed**.
7. An **anti-overengineering** clause (only what's asked; no new deps/abstractions beyond the task).

Apply the improver transform — structure/sections → role + the *why* → success-criteria + a self-check
→ tighten — **minus prefills** (prefills are deprecated on Claude 4.6+ and error; never emit one).

## 3. Re-resolve and route

The request is now sharp. Re-apply the resolvability test (`residue-gate.md` Step 1–2) to the
**sharpened** form and route:
- resolves to **dc** (visual layer) → hand off the sharpened scope (structured constraints only — no
  hook/narrative; see genesis's design-handoff discipline).
- resolves to **code-review** (audit/bug) → the implement→review→apply→re-review loop, scaled to risk.
- resolves to **genesis** (became a feature in a managed project, or project-scale) → genesis replan.
- small direct task in no engine's domain → execute it.

## 4. Quiet + cancelable

Sharpen **silently** — never narrate the refinement ("I'll restructure your request as…"). Show the
sharpened prompt (or just proceed/route). The user can **cancel in one word** ("no" / "stop" /
"сам") and refiner steps fully aside.

## Worked example (vague residue → routed CC-prompt)

Input (non-managed repo): *"everything's slow, take a look"* → residue (no engine starts).
Refiner discovers via tools (step 1): the slow path is `GET /dashboard/items`, an N+1 in
`items.py:fetch_items`. No clarifying question needed (exploration settled it). Sharpened:

```
Task: fix slow load on GET /dashboard/items (one outcome).
Files: api/dashboard/items.py (handler), api/db/queries.py.
Symptom: list endpoint p95 ~3s at ~500 items.   Likely: N+1 in items.py:fetch_items.
Acceptance: p95 < 300ms at 500 items; response shape unchanged.
Verify: pnpm test dashboard/items.spec.ts (and time the endpoint locally).
Reference: the batched-query pattern in api/orders/queries.py.
Constraint: fix the N+1 only; no new deps, no broader refactor.
Route: implement, then code-review (perf surface) → apply → re-review.
```

The same input in a **managed** project would not reach here for a *feature*, but a *bug* like this
still does (a bug is locatable code → it resolves to code-review directly; refiner only steps in when
even the locating is unclear).
