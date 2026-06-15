# Diversity — the axis-spread map and enforcement

Companion to `concept.md` (the hook must not collapse into one mechanism), `page-architecture.md`
(archetype as a fourth axis), and `memory.md` (the sameness ledger). Those state the *principle*;
this file makes diversity **mechanically enforced** instead of hoped-for, via `tools/spread.mjs`.

The failure this fights: best-of-N generation collapses to N variations of the *same* structural
idea (same archetype, same hook mechanism) wearing different palettes — "different, not diverse".
The cure is to assign each candidate a **different cell** of an explicit map before generation,
and to keep a ledger with teeth so the engine doesn't drift back to its favourite cell across a
session/project.

## The map — Category × Type × Idea

Three axes, the first two **enumerable** (so collision is detectable), the third the creative fill:

- **Category = page archetype** (`page-architecture.md`), 8 cells:
  `classic-landing · continuous-canvas · editorial-longread · index-directory ·
  horizontal-sideways · split-two-track · single-scene-focus · conversation-reveal`.
- **Type = hook mechanism** (`concept.md`), 6 cells:
  `scroll-morph · cursor-pointer · reframed-navigation · living-system ·
  structural-typographic · input-participation`.
- **Idea = the concept itself** — the specific hook for *this* brief, invented fresh (never reused;
  `concept.md`'s Verbalized-Sampling step produces 4–6 candidates with likelihoods).

Category × Type = **48 structural cells.** Aesthetic family (`aesthetic-families.md`, ~14) is a
character overlay on top, used to further separate candidates that must share a structural cell.
A candidate's **fingerprint** is `{archetype, mechanism, family}`.

## How the work loop uses it (best-of-N)

1. Before generating the N candidates, run `tools/spread.mjs assign <brief> <N>`. It returns N
   **distinct** `{archetype, mechanism}` cells, *avoiding* cells used recently in this project
   (read from `.design/ledger.json`), and biased toward the tail (under-used cells) — so the set
   is structurally spread by construction, not by luck.
2. Generate each candidate **into its assigned cell.** Candidate 1 is a continuous-canvas /
   living-system; candidate 2 a split-two-track / structural-typographic; etc. Structural collapse
   is now impossible — the critic then picks the best *expression*, not the only structure that
   survived.
3. When the owner/critic picks a winner, `tools/spread.mjs commit <archetype> <mechanism>
   --family <F> --brief <B>` records the chosen cell to the ledger and logs its **novelty
   percentile** (how under-used that cell was — the tail-percentile) to `.design/spread-log.jsonl`.

## Enforcement (the teeth on the sameness ledger)

`memory.md` defines the ledger as a *soft flag*. Diversity adds a hard check for the
inertia-collapse case:

- **Collision = an unpinned exact-cell repeat inside the last-K window** (default K=8). On collision,
  `spread.mjs check` returns `verdict: REROLL` — the engine must pick a different cell (or justify
  the repeat explicitly as deliberate, which a human can accept). ε is structural-distance: same
  archetype **and** same mechanism = distance 0 = reroll; differ on one axis = distance 1 (allowed
  but noted); differ on both = distance 2 (ideal).
- **Pinned devices are exempt** (favourites pin, `memory.md`) — deliberate brand consistency is not
  collapse. The check honours the pin and returns `OK_PINNED`.
- **The log enables measurement.** Without `spread-log.jsonl` we can't tell whether the machinery
  actually spreads outputs or we just believe it does — `evals/diversity.mjs` reads the fingerprints
  and reports min/mean pairwise distance, failing if outputs cluster.

## Status

**SITUATIONAL with teeth.** Active whenever persistent state (`.design/`) is available: the
assign→generate→commit cycle is the default for any multi-candidate build, and the collision check
is a real reroll, not just a flag. Silently degrades to the soft flag (`memory.md`) when state is
unavailable. Never overrides invariants, governance, or accessibility; a pinned favourite always
wins over the spread.
