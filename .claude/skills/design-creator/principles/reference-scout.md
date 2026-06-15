# Reference-scout — feed imagination from the live web, not the frozen median

The engine's default output is the median of its training — that is the root of slop and of
timidity (`anti-slop.md`, `ambition.md`). The cure for *imagination* (not just for tells) is
to look at what's actually winning right now and pull **techniques and structure** from it.
This module is how the engine stocks its vocabulary before forming the hook.

## When to run

- On expressive briefs (brand / marketing / portfolio / launch / product story) at the survey
  stage, **before** committing the hook and signature.
- When the user explicitly wants "something like awwwards / Active-Theory / Igloo-tier".
- When the engine catches itself reaching for a generic archetype — that's the cue to go look.
Not on app surfaces, internal tools, or tiny edits (it's for ambition, not utility).

## Sources, in priority order

1. **The user's own refs.** Read `.design/refs/` — any site URLs, screenshots, or a notes file
   the user dropped in. **These win over everything** — they're the most direct read on taste.
   Also read `references/inspiration.md` (the curated, owner-approved pack) when present.
2. **Curated platforms** (live web search / fetch): Awwwards (Sites of the Day / collections),
   FWA, Codrops (case studies + demos — these come *with technique write-ups, the gold for
   us*), Httpster, Godly, Land-book, and the sites/blogs of studios working at this tier.
3. **Technique-specific digs:** when a beat is chosen (a scroll-tied path, a 3D hero, kinetic
   type), search Codrops/CodePen/case studies for current implementations of *that move*.

## What to extract — and the hard copyright line

Extract the **approach**, never the asset or the code:
- the structural idea (how the page is paced; what the signature device is; how the hook is
  enacted), the technique (a scrubbed shader reveal, a pinned step-builder, an SVG path-draw),
  the palette/typography *strategy* (one accent + neutral scale; a display face's role).
- **Do NOT copy** markup, CSS, shader code, copy text, images, models, or a site's exact layout.
  No cloning a site, no lifting its assets, no reproducing its content. Reproducing a real
  studio's site is both a copyright violation and the opposite of a signature — it's slop with
  extra steps. You are learning the *grammar*, then writing your own sentence.
- **Cite** what informed a decision in `.design/journal.md`: "pinned-reveal pacing informed by
  <studio/case-study>" — so the lineage is honest and auditable, not passed off as conjured.
- Assets come only from the licensed sources in `3d.md` (CC0/CC), never scraped from a reference.

## How it feeds the work

- The scout returns a short **inspiration brief**: 3–6 reference points, each one line of "what
  to steal at the idea level" (a device, a structure, a pacing trick) — not a gallery dump.
- That brief feeds `concept.md` (the hook), `signature.md` (the one memorable device), and the
  storytelling spine (`storytelling.md` → the multi-beat plan).
- It also raises the ceiling for the ambition check (`tools/ambition-check.md`): the pairwise
  "in-tier?" comparison is more honest when the engine has actually seen the current tier.

## Reference-conditioning (how the pulled refs feed generation)

The point of scouting is to **move the generator's prior** off the median, not to admire sites.
So: pull **3–5** exemplars of the chosen family, retrieved on **similarity *and* diversity** (five
near-identical refs collapse you into one look — spread them), extract each one's **technique &
structure DNA** (the composition move, the rhythm, how the focal moment is built — never assets,
markup, shader, or copy), and generate by **transposing that DNA onto this content**. Few-shot
exemplars reliably shift the distribution; this is move 1a of "Making the first try land" in
`SKILL.md`. Cite the lineage in `.design/journal.md`.

## Discipline

- Time-box it (a handful of searches, like the main web budget) — scouting is to spark the
  hook, not to replace the work. Don't rabbit-hole.
- Surface confidence: if the scout couldn't find strong current references for a niche brief,
  say so rather than inventing a trend.
- Never let a reference override the floors: a11y, domain-fit, perf, and reduced-motion still
  gate, no matter how cool the inspiration was.

## Refreshing the tells (the anti-slop catalog)

`principles/tells-current.md` is the dated, provenanced half of anti-slop. It carries a
`last_refreshed` date and a `refresh_interval_days` (30). When `tools/preflight.mjs` reports
`tells.status: stale`, the engine runs a **tells-refresh** pass — a focused scout pass whose job
is to keep the catalog current without churning the stable principles in `anti-slop.md`.

Procedure (the engine **proposes**, never auto-edits):
1. **Scout the current median.** Web-search recent AI-generated / template / "startup landing"
   output for the visual, component, and copy patterns that now read as "this is AI" — the same
   way the existing tells were identified. Look specifically for (a) **new** tells not yet in the
   catalog, and (b) **fading** tells whose recognition value has dropped (they appear less, or
   have become legitimately mainstream).
3. **Produce a reviewable diff**, not a rewrite:
   - **ADD** — new tell + `first_seen` (now) + `source` (where observed) + `status` (`active` or
     `watch`). An add needs a real citation, never a guess.
   - **RETIRE** — move a tell to the graveyard with the date + the reason it's no longer a reliable
     signal. Retiring is held to the same bar as adding: a stale tell left active causes false
     positives on legitimate design, so retirement is a real, provenanced decision.
4. **Owner approves the diff.** On approval, apply the changes and bump `last_refreshed` to today.
   Nothing in the catalog changes silently; the generalized rules in `anti-slop.md` are untouched.

This keeps the durable reasoning stable and the volatile instance list current on a cadence,
instead of letting the whole anti-slop file rot or be rewritten wholesale.

## Status

- Running the scout on expressive briefs before fixing the hook: **MUSTHAVE-DEFAULT** (the
  engine may skip it only for a stated reason — e.g. the user supplied rich refs already).
- Extract techniques/structure, never assets/code; cite the lineage: **MUSTHAVE-BASE**.
- The owner-curated pack lives in `references/inspiration.md`; user drop-ins in `.design/refs/`.
