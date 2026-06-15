# Modes — Clean & Statement

Mode is the **intensity axis** of the design. It is not a separate body of rules — it is a **filter over the per-technique statuses** defined across the `principles/` files.

## Two modes only

There are exactly two modes. More were considered and rejected: middle modes blur the boundary (Claude would constantly guess which of three a task is), and they make the survey heavier. Real nuance comes from three other mechanisms — see below.

## What each mode activates

**Clean**
- Active: MUSTHAVE-BASE, MUSTHAVE-DEFAULT. SITUATIONAL techniques are *available* (not blocked) but, by definition, applied only after being proposed in the survey and approved — never auto-on. "Available in Clean" ≠ "on by default".
- Blocked: STATEMENT techniques.
- In practice: layout level 0–1, calm motion, the baseline storytelling set, a restrained typography subset.

**Statement**
- Active: everything Clean has, **plus** STATEMENT techniques unlocked.
- In practice: layout level 2–5, expressive motion, the full storytelling arsenal, 3D / kinetic type / pin sections available.

## Canonical mapping

The mode -> layout-level mapping (Clean = level 0-1, Statement = level 2-5) lives **here** and in `layout.md`'s ladder. Other files (`color.md`, `typography.md`, patterns) should *reference* it, not restate it, so a future change is made in one place.

## One switch, all files

Mode is set once (survey Q2) and applies across **every** `principles/` file at once. The result is a coherent design — never "calm typography + wild motion". Mode sets the *ceiling* of expression.

## Default intensity — bias toward Statement

The mode is **chosen against the brief, with a bias toward Statement** whenever expression is welcome. Statement is the default for brand sites, marketing, portfolios, product launches, anything telling a story or selling a feeling. **Clean is a deliberate choice of restraint** — for utilities, enterprise dashboards, accessibility-first tools, data-dense app surfaces, sensitive contexts — not the safe fallback the engine reaches for when unsure. Picking Clean "to be safe" on an expressive brief is the timidity failure (`ambition.md`): it silently removes access to 3D, pin, kinetic, and the full storytelling arsenal. If unsure whether a brief wants expression, assume it does and propose Statement, then dial down only for a concrete reason.

## Nuance without more modes

Finer control comes from three mechanisms, not from adding modes:
1. **Aesthetic family** — terminal-core even in Statement is more restrained than playful.
2. **Intensity by hierarchy** — within a mode, the hero is rich, an ordinary section is calmer.
3. **Point overrides** — the user may request a single Statement technique inside a Clean project; Claude does it as an explicit override.

Mode is a strong default, not a cage — and the default leans bold. A Clean result on a brief that wanted a showpiece is a failure of nerve, not a safe choice (`ambition.md`).
