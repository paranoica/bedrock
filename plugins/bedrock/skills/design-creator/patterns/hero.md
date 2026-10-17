# Pattern: Hero

A section recipe. This file gives Claude **what to assemble**, not what to copy. The visual is built to the project's design system; the structure is universal.

## 1. Purpose

The hero is the first thing the visitor sees. Its job: in seconds, communicate what this is and why it matters, and set the design's tone for the whole page. It must create the strongest single impression on the page.

## 2. Block composition

**Required:** a headline (the hero word/phrase), a primary CTA.
**Optional:** an eyebrow / kicker line above the headline, a subheadline, supporting media (image / 3D object), social proof (logos, a rating, a count), a secondary CTA.

## 3. Order logic

Eyebrow (small, sets context) → headline (the dominant element) → subheadline (one clarifying line) → CTA (the action) → optional social proof (trust, immediately after the action). Media sits beside or behind this stack depending on layout level. The eye must land on the headline first — it is the largest, highest-contrast element.

## 4. Variants by mode

- **Clean** — left-edge or centered stack, layout level 0–1; typography uses scale + density + tracking; a calm scroll-reveal entrance.
- **Statement** — asymmetric or overlap layout (level 2–5); full 7-technique typography stack; word-by-word reveal; optional 3D accent object; expressive entrance.

## 5. Technique bindings

- Typography: hero uses 6–7 techniques in Statement, a restrained subset in Clean (`principles/typography.md`).
- Entrance: scroll-reveal is default; word-by-word reveal is a Statement option (`principles/storytelling.md`, `principles/kinetic-type.md`).
- Optional 3D accent: `principles/3d.md` — "light" level.
- Living background optional: `principles/decorative-graphics.md`.

## 6. Typical mistakes

- A headline with no technique applied — the #1 cause of a boring hero.
- Two hero-sized words competing — mush, not composition.
- Centered single-column stack as the only option in Statement — slop.
- A flat lone photo rectangle instead of composed media.
- Accent color spread across the whole hero instead of one point.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.

## Recipe: full-bleed media + oversized type

One of the dominant award-winning hero shapes in 2026, when the brief supports it:
- A **full-bleed** image or muted video sets the mood edge to edge; **oversized type** carries the message on top (the words are the design element, not a label on the image — `typography.md`).
- The media gets a legibility treatment (scrim/gradient/panel) so the type stays readable in both themes (`composition.md`, `depth.md`).
- Type can be one giant hero word + small supporting line; optional kinetic weight via a variable font.
- Performance: the hero image is the LCP element — `priority`, explicit dimensions, responsive sources, no layout shift (`seo.md`). Heavy video respects the perf budget and `prefers-reduced-motion` (static poster frame).
- Fits Statement and branded landings; for app surfaces use a calmer titled header instead.
