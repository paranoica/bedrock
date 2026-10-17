# Page Architecture

The file that fixes "every site comes out the same". `layout.md` governs composition *inside* a section. This file governs the **skeleton of the whole page** — which sections exist, in what order, and how the page is paced. Two sites with different fonts and colors still feel identical if they share one skeleton. They usually do, because there is a default skeleton the model reaches for: nav -> hero-with-an-object -> stat strip -> card grid -> quote -> CTA -> footer. **That default is banned as a default.** It may be chosen, deliberately, when it genuinely fits — but it is never the automatic answer.

## The rule

Before generating, the engine picks a **page archetype** for this specific project, the same way it picks an aesthetic family and a mode. The archetype is stated in the narrative and approved at the gate. It is chosen from the library below — or invented — but it is chosen *consciously*, against the brief, never defaulted into.

Two different projects in one session must not receive the same archetype unless there is a real reason. If three layouts in a row share the nav->hero->strip->grid->quote->cta spine, that is a structural failure flagged by QA.

## The archetype library (not exhaustive — invent too)

**1. The classic landing.** Hero -> proof -> features -> testimonial -> CTA. The default — powerful, and exactly why it must be *chosen*, not defaulted. Best when the job is straightforward conversion and the visitor wants the standard reading order.

**2. The single continuous canvas.** No discrete stacked sections — one uninterrupted surface the visitor moves through, content entering and leaving as a continuous space (a map, a timeline, a long horizontal pan, a single 3D scene). The "sections" are moments in one space, not boxes.

**3. The editorial / long-read.** Paced like a magazine feature: a strong opening spread, then prose with pull-quotes, full-bleed images, captions, asides, chapter breaks. Reads as an article, not a product page. Best for studios, brands with a story, journalism, anything where the *telling* matters more than a feature list.

**4. The index / directory.** The content itself is the structure — a catalogue, an archive, a list-as-architecture. The page is organised the way the thing is organised (by date, by type, by room, alphabetically). Navigation through the index *is* the experience.

**5. The horizontal / sideways.** The page moves left-to-right, or mixes vertical and horizontal panels. Breaks the universal vertical-scroll assumption. Best for portfolios, galleries, timelines, anything sequential.

**6. The split / two-track.** The viewport is divided — one side fixed, one side scrolls; or two columns telling parallel stories; or a sticky visual with scrolling text beside it. The relationship between the two tracks carries meaning.

**7. The single-scene focus.** One thing — a product, an object, a 3D model, a single idea — and the entire page orbits it. Minimal sections; the page is almost a poster with depth. Best when there is exactly one hero thing and saying less is the point.

**8. The conversation / sequential reveal.** The page unfolds as a sequence of beats, almost like slides or chapters — each full-height moment is one idea, revealed in turn. Best for narrative, onboarding, storytelling-heavy briefs.

## Pacing — the rhythm of section heights

Skeleton sameness also comes from **every section being the same height and the same density.** A page has rhythm: a tall immersive opening, a short tight band, a long calm reading stretch, a sharp punchy break. Vary section height, density, and "loudness" deliberately — a flat sequence of equal medium-height sections is the visual signature of slop, even when each section is individually fine. Intensity by hierarchy (`layout.md`) applies to the *page*, not only within a section.

## Relationship to the other axes

- Aesthetic family = character. Mode = intensity. Hook = idea. **Archetype = the shape of the page.** A fourth independent axis.
- The same hook lands differently in different archetypes — a "watch it assemble" hook is one thing in a single continuous canvas, another in an editorial long-read. Archetype is chosen alongside the hook, not derived from it.

## Broken / anti-grid archetype

A consciously broken grid is a valid page archetype for the right domain — overlap, bleed, off-rhythm placement that reads as authored tension. Use only from an established grid and never at the cost of readability; guard against trust-sensitive domains. Full rules in `layout.md`.

## Status

Choosing a page archetype consciously per project, never defaulting to the classic landing, not repeating an archetype across projects without reason, varying section pacing: **MUSTHAVE-BASE**. A deck of layouts that all share one skeleton fails the QA gate.
