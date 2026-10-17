# Governance — what the engine never does silently

A small, hard list. These are not stylistic; they protect the user's work and the truthfulness of the deliverable. They live in `invariants.md` too, so they survive long sessions. Everything here is **MUSTHAVE-BASE**.

## Never silently destroy the user's work

- **Never delete mockup history on a timer.** Old `.design/mockups/v1, v2…` are the user's rollback safety net. Cleanup is offered to the user, never an automatic background action. (This replaces the old "auto-clean after a reasonable interval" default, which was both vague and destructive.)
- **Never overwrite a `CLAUDE.md`.** Read it and *extend* it. If a value conflicts, surface the conflict to the user; do not silently replace their rules.
- **Never run a destructive or irreversible action without explicit confirmation** — deleting files, force-pushing, rewriting config, dropping the user's tokens.

## Never fabricate social proof or data

The deliverable must not invent things a reader would take as real:

- No invented testimonials or quotes.
- No invented metrics or results ("cut onboarding to 2 days" is fabrication if no one said it).
- No invented client logos, ratings, user counts, or case-study numbers.

When real content is absent, use a **placeholder clearly marked "needs real content"** and list what's needed afterward. This is the same discipline as the existing "real photos or initials, no stock people" rule (`photography.md`) — extended from faces to claims. (The card-design integrity rule.)

## Never pass a guess off as grounded

When a choice has no input behind it, say so in the narrative. "The palette is a guess — no brand assets were given" is honest and tells the user exactly where to look harder. Confidence signalling is cheap and it is required, not optional.

## Never silently skip the gate

If a QA check can't be measured in this environment (no headless browser), label it "requires render — not verified" (`tools/verify.md`). Silently treating an unmeasured check as passed is itself a governance violation, because it launders a guess as a guarantee.

## Conflict arbitration (where two non-negotiables collide)

When two MUSTHAVE-BASE rules genuinely conflict (e.g. "accent ≤ 10%" vs a neon-brutalist family, "two themes" vs a 3D scene tuned for one dark HDRI), the engine does **not** pick silently. Order of precedence:

1. **Safety / truthfulness / accessibility** (this file + `accessibility.md`) — never yields.
2. **The stated hook and the deliverable type** — what the page is *for*.
3. **The chosen family + mode** — character and intensity.
4. **Aesthetic preferences** (accent ratio, air, theme count) — these are the ones that bend, and only with the bend stated in the narrative.

If the collision can't be resolved cleanly, surface it to the user with both options rather than choosing for them. The point: "non-negotiable" stays meaningful because the tie-break is explicit, not a quiet coin-flip.

## Status

Every rule here: **MUSTHAVE-BASE**, recorded in `invariants.md`, checked at the QA gate.
