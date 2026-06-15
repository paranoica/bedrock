# Color

## The palette structure (always the same)

A palette is built as a ladder, in this order:

`background → surface → border → secondary text → primary text → exactly one accent`

Top-tier design almost never uses five competing colors. It uses a flawless neutral scale plus **one** accent point. "More premium than Vercel" is not "more colors" — it is a more considered neutral scale and bolder typography.

## Three rules that separate expensive color from cheap color

**Black is never `#000`.** Always a near-black (`#0A0B0C`-ish) or a colored near-black (a green-black, a navy-black, a wine-black). Pure `#000` is flat and cuts the eye.

**White is never pure `#FFFFFF` for a light theme.** A light theme reads more expensive on a warm cream (`#FAF8F2`-ish) than on raw white.

**Text is never pure black/white on color.** Warm-black, navy-black, near-white. A 5% brightness shift is the difference between "studio" and "template". On a colored fill, text takes a very dark or very light stop of that *same* color family — never generic black/gray.

## The accent

- The accent covers **at most ~10% of the screen**. Button, link, one underlined word, the cursor. The moment accent spreads, the design reads cheap.
- The neon-brutalist / Igloo approach in the extreme: the whole site is monochrome and color strikes only at points.

## "Ishness" — why indigo/violet feels like AI

The reason purple/indigo feels like default AI output is that it is soft and slightly washed-out in a way the model gravitates to. Avoid it as the default accent. What *does* work: muted, slightly desaturated accents with intent behind them — a lime, a warm orange, a clay, a considered teal. Color is grounded in the product's story, not picked because it is "nice".

## Choosing a palette (the method the engine uses)

1. Pick the background tier first (dark-first or light/cream).
2. Derive surface and border as small steps off the background — never large jumps.
3. Set secondary and primary text as warm/cool near-blacks or near-whites.
4. Choose exactly one accent, grounded in the product and the aesthetic family. Optionally a second accent in a strict ratio (e.g. 70/30) only if the family calls for it.
5. Check contrast: body text ≥ 4.5:1; large text ≥ 3:1.

## Color space — OKLCH for scales, Oklab for gradients

Generate and reason about color in perceptual space, not sRGB hex:

- **Palette scales / shade ladders → OKLCH.** Stepping lightness/chroma in OKLCH gives evenly-spaced shades that *look* evenly spaced; equal sRGB steps don't. Define the neutral ladder and the accent tints this way.
- **Gradient interpolation → Oklab.** Interpolating a two-color gradient in sRGB collapses through a muddy gray middle; OKLCH keeps chroma but can swing hue through unintended colors; **Oklab** runs the straight perceptual line — clean, predictable midpoint. Use `linear-gradient(in oklab, …)` (Tailwind v4 already defaults gradients to Oklab). This was eyeball-confirmed: sRGB midpoints go dirty, Oklab stays true.
- Provide an sRGB fallback for the rare engine without `in oklab/oklch` support; the property degrades to a default-space gradient, so order the stops so that's acceptable.

## Neutrals are never neutral (tinted)

The neutral scale carries the personality. A warm grey (a hair of orange/red in it) and a cold grey (a hair of blue) produce completely different products from the same layout. Tint the whole neutral ladder consistently toward the brand temperature — never use a dead `#888`-family grey. This is what makes a "just neutrals + one accent" palette read as designed rather than empty.

## Dark is its own palette

A dark theme is not the light palette inverted. Re-derive the dark neutral ladder (elevation = lighter surface, not deeper shadow), and re-check accent chroma — an accent that pops on cream often goes muddy or glaring on near-black. See `depth.md` and `theming.md`.

## Color and 3D

When the project has 3D, the 3D object is part of the color system, not separate. An emissive material in the site's accent color, plus Bloom postprocessing, makes the 3D object the source of the site's glow. Glass/metal materials reflect the environment — pick the HDRI so reflections sit in the palette. 2D palette and 3D look are one system.

## Choosing the palette — proven directions over invented ones

Inventing a palette from scratch is where amateur work shows. Anchor the choice in a direction that is known to read as sophisticated, then execute the ladder precisely:
- **Single-hue tonal range.** Eight shades of one hue (eight blues, eight greens) — the cohesion is something multi-color palettes cannot fake. The strongest default for professional/luxury work.
- **Warm neutral + one earth accent.** Taupe / sand / warm-off-white base with a terracotta, clay, olive, or rust accent. Grounded, human, current — and the opposite of the cold purple-on-white AI default.
- **Inky black + one metallic or warm accent.** Deep near-black with a single gold, amber, or warm accent — drama through restraint, not through more colors.
- **Muted, not candy.** Where color is wanted, use the desaturated version — dusty rose over hot pink, sage over neon green, powder blue over electric. Maturity reads as muted.

Whatever the direction: the neutral scale carries the personality (neutrals are never truly neutral — a warm grey and a cold grey change everything), and exactly one accent does the pointing. CTA color matters less than CTA *contrast* against its surroundings — a high-contrast accent on its background is what performs.

When unsure whether a palette works, it is legitimate to look at real award-winning sites in that niche for reference rather than guessing — but reference the *relationships* (how dark the base is, how saturated the accent, how much accent appears), never copy hex values.

## Status

- Palette-ladder structure, one-accent discipline, no-pure-black/white: **MUSTHAVE-BASE**.
- Anchoring the palette in a proven direction rather than an invented one: **MUSTHAVE-BASE**.
- A second accent, decorative color play: **SITUATIONAL** — proposed in the survey.
