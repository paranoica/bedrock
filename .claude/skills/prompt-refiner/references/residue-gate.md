# Residue-gate — the activation decision procedure

prompt-refiner activates **only** on residue. This file is the decision procedure that decides
residue-or-not. It runs BEFORE anything else, and most of it is invisible to the user.

## Step 0 — the classification is CHEAP, SILENT, and is NOT an intervention

Before the table below can apply, refiner must read the request and decide which engine it resolves
to. That read is a **cheap, silent judgment** — not "running the refiner". It costs the user **zero
words and zero delay**. Refiner becomes *visible* only when the verdict is **residue**. "Read and
yield" is invisible: the request is handed to the owning engine with no refiner output at all.

Keep the classification bounded: it needs only enough understanding to pick *an engine or residue* —
**not** enough to sharpen a perfect prompt. If you notice you are basically sharpening the request
just to classify it, that is itself weak evidence of residue — but **default-yield still wins**: when
unsure, yield silently (Step 3). Never turn the classifier into an ambient layer in front of every
request.

## Step 1 — the resolvability test (the criterion)

**Does the request resolve to ONE profile engine that can start as-is?**

- **Resolves to one engine** (even if vague *inside* that engine — the engine will start and ask its
  own ≤1 question) → route there, **refiner silent**.
- **Does not resolve** — it doubles *between* engines, or resolves to no engine, or there is no target
  to start on → **residue → refiner takes it**.
- A clear small task in no engine's domain (target + goal both present) → just do it, **refiner silent**.

Heart of it: **vague WITHIN one engine → that engine (it asks). Doubles BETWEEN engines / no target →
residue.** The discriminating line is *resolvability + startability*, never *topic*.

Engines and "can start as-is":
- **design-creator** — resolves to building/redesigning a visual surface (page/screen/component exists
  or is named); it surveys for the rest.
- **code-review** — resolves to a locatable piece of existing code to audit/debug.
- **genesis** — resolves to project inception/planning **at project scale** (broad is fine — turning
  broad into specifics is genesis's job), OR (see Step 2) a feature/new-work request in a
  genesis-managed project.

## Step 2 — the managed-project branch (where feature requests go)

A feature / new-work request ("add a reviews section", "support refunds") is not inception and may not
obviously double between dc/code. Resolve it by **whether the project is genesis-managed**:

- **Managed** — `docs/` + `genesis.tasks.json` exist (cheap check: glob for them). → the feature
  resolves to **genesis (replan)**: replan amends the spec first (a targeted interview on the delta
  → anchor it), then re-derives so the new task enters the backlog; the execution-loop builds it.
  **refiner silent.** Sharpening a feature straight to code here would bypass the spec and backlog —
  the exact desync the anchor mechanism exists to prevent.
- **Not managed** — no `docs/` + `genesis.tasks.json` (refiner is working in a foreign repo). → there
  is no backlog to respect; **refiner takes it**, sharpens into a CC-prompt, and routes (to dc / code
  / direct execution per the resolved target).

So managed-ness is part of resolvability: in a managed project more requests resolve to genesis and
refiner stays quiet; in a foreign repo refiner is the catch-all sharpener.

## Step 3 — default-yield on doubt (quiet by default)

Borderline whether an engine could start? **Default = yield to the engine; refiner stays silent.**
False silence is cheap — the engine asks its own clarifying question (dc surveys; code-review "if
unclear, ask"; genesis interviews). False interception is costly — an extra round of questions on a
request an engine could have taken. **On doubt, refiner yields.**

## Discriminating pairs (run by the criterion, not the topic)

| Request | Resolves to one engine that can start? | Verdict |
|---|---|---|
| "make the button nicer" | yes — button exists → dc-edit (or direct); dc starts + surveys | dc · **silent** |
| "do something about onboarding, it's bad" | no — doubles: redesign(dc)? broken flow(code)? copy? no target | **residue → refiner** |
| "why does test_auth.py::test_expired fail" | yes — locatable target; code-review/debug starts | code-review · **silent** |
| "everything's slow, take a look" | no — which flow? measured where? no engine starts | **residue → refiner** |
| "I want to launch a storage-rental service" | yes — inception; genesis starts its interview | genesis · **silent** |
| "make the landing punchier" | yes-ish — resolves to dc; vague *inside* → dc surveys (default-yield) | dc · **silent** |
| **"add a reviews section"** — in a **managed** project | yes — resolves to **genesis replan** (feature → spec+backlog) | genesis · **silent** |
| **"add a reviews section"** — in a **non-managed** repo | no managed backlog to respect → refiner sharpens + routes | **residue → refiner** |

The last two are the **same phrase**, split only by managed-ness — that is why managed-ness is in the
criterion, not a side note.

## The leak rule

If refiner ever takes a request a profile engine could have started as-is → the **residue-test leaks**.
Fix the test (this file), **do not add a special-case rule**. Counting clean boundaries, not rules.

## Branch hygiene (do not merge)

**Yield** (Steps 1–3) is the take-or-not decision. The **≤1 clarifying question** (`refine-algorithm.md`)
is something refiner does **only after it has already taken** a residue request, to sharpen more
precisely. They are different branches: refiner never "yields to an engine *and* asks a question" on
one request. Yield = don't take. Question = took, now sharpening.
