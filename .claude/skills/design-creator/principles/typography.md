# Typography

## The core idea: "wow" is a stack of techniques, not a font choice

A boring headline is boring **not because the font is wrong** but because no technique was applied to it. The same text in the same typeface goes from "default, whatever" to "award-site" purely by stacking techniques. Each technique adds one thing; each alone is small; together they compound.

## The seven techniques, in order of strength

1. **Scale** — the strongest. Simply large is already better.
2. **Density (line-height < 1)** — packs a multi-line headline into a "brick", the expensive look.
3. **Negative tracking** — on large sizes, almost always a plus.
4. **Weight contrast** — Thin next to Black, builds hierarchy within one phrase.
5. **Size contrast** — one hero word gigantic, the rest small.
6. **Accent word in a different typeface / color** — the semantic center.
7. **Asymmetric setting** — text as a composition in space, not a line.

## The intensity matrix

Not every text element gets all seven. Intensity by hierarchy:
- **Hero** — 6–7 techniques.
- **H2 / section heading** — 1–3 techniques.
- **Body** — 0 techniques.

## Two iron constraints

- **Tight line-height and negative tracking apply only to large sizes.** On body text this is unreadable. Body goes the opposite way: line-height 1.5–1.7, tracking 0.
- **The hero word must be one.** Two giants in one phrase is mush, not composition.

## Three font roles

A project picks fonts for three roles (one font may cover more than one):
- **Workhorse grotesques** — body, UI, dense text. Readable, neutral, characterful enough.
- **Characterful faces** — headings with personality.
- **Display faces** — the largest hero moment, maximum character.

## Cyrillic check (mandatory)

Before committing any typeface, verify it has the glyphs the project needs. Many display/serif faces ship Latin-only — if the project has Cyrillic (or any non-Latin) content, a Latin-only accent face will force ugly fallbacks. Always check coverage; have substitutes ready (for a serif accent with Cyrillic: faces like Cormorant, PT Serif, Bitter).

## Fine craft (the details that read as "typeset", not "typed")

- **Real punctuation**: curly quotes `" "` and apostrophes `'`, en/em dashes, a real ellipsis — never straight quotes or `--`.
- **Tabular figures** (`font-variant-numeric: tabular-nums`) for any aligned numbers — tables, prices, dashboards, stats — so digits don't jitter.
- **Measure** (line length) 45–75 characters for body; cap it with `max-width` in `ch`. Long lines are the most common readability failure.
- **Widows & orphans**: prevent a single dangling word on headings/CTAs with `text-wrap: balance` (headings) and `text-wrap: pretty` (body) where supported; non-breaking spaces before the last word as fallback.
- **Hanging punctuation** and edge alignment → see `optical.md`.

## Variable fonts (technique)

A variable font is one file spanning the whole weight (and often width / optical-size) range continuously, and the axes are **CSS-animatable**. Two wins: a cheap source of "expensive" kinetics — a heading that thickens on hover or along scroll via `font-variation-settings` / `font-weight` transition — and a lighter page (one file instead of light/regular/bold…), which helps Core Web Vitals (`seo.md`, `optimization.md`). Constraint: variable Cyrillic coverage is thinner than Latin, so the mandatory Cyrillic check applies doubly — confirm the axes work for the project's glyphs before relying on them. Keep weight kinetics on headings/key moments, never on body or nav (readability first).

## Numbers as typography

Metrics are a design element, not plain text: set a hero stat gigantic, the unit/label small and quiet beside it, tabular figures so a row of them aligns. A big honest number is one of the strongest, least-slop hero devices (and pairs with `data-viz.md`).

## Fluid type & space

Drive type sizes (and the matching spacing) as one fluid system — `clamp()` with a consistent ratio — rather than hand-set values per breakpoint. One scale that interpolates smoothly removes breakpoint jumps and a class of CLS surprises. See `responsive.md` for the shared fluid engine.
## Status

- Three-role discipline, Cyrillic check, the two iron constraints, real punctuation, tabular figures for aligned numbers, sane measure: **MUSTHAVE-BASE**.
- Widow/orphan control, fluid type scale, numbers-as-typography: **MUSTHAVE-DEFAULT**.
- Variable-font weight kinetics: **SITUATIONAL** (proposed; taste/perf permitting) — but using a variable font for payload savings is encouraged whenever coverage allows.
- The seven-technique stack on the hero: **MUSTHAVE-DEFAULT** in Statement; in Clean apply a restrained subset (scale + density + tracking).
