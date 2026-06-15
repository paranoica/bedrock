# Reference: Statement-mode exemplar

A worked example of a coherent Statement-mode site — the 2D/3D blend with oversized typography and page-level storytelling. Illustrates how the principles compose at full intensity. A demonstration, not a verbatim template.

## Aesthetic family
Cinematic dark (works equally as neon-brutalist).

## Color (ladder)
- Background: a colored near-black (a deep navy-black or green-black), never `#000`.
- Surface / border: small steps off the background.
- Text: warm/cool near-whites, never pure white on color.
- Accent: one saturated color, struck at points (~10%) — and carried into the 3D object as an emissive material, so the 3D becomes the source of the site's glow.

## Typography
- Hero: the full 7-technique stack — large scale, line-height < 1, negative tracking, weight contrast, size contrast, an accent word in a second face, asymmetric setting.
- Display face at maximum character; one workhorse grotesque for body.
- One hero word only.
- Cyrillic checked; a Cyrillic-capable serif substituted for the accent word if needed.

## Layout
- Level 2–5: asymmetry and overlap, edge-to-edge bleeds, grid-breaking. Hero is overlap-heavy; ordinary sections sit calmer (intensity by hierarchy).

## Motion
- MUSTHAVE + STATEMENT: 3D tilt, glow-following cursor, word-by-word reveal, glossy text sweep — all dosed, all `transform`/`opacity`, all with `prefers-reduced-motion` fallback.

## Storytelling
- Full arsenal: pin sections, scroll-driven 3D, strong parallax, word-by-word hero reveal. At least one surprise moment; rhythm of dense/air; the page is a sequence, not a stack.

## 3D
- "Through-line" level: a 3D object bound to scroll, passing through sections, camera moving. Glass (`MeshTransmissionMaterial`) + emissive accent, Bloom postprocessing, an HDRI environment. Mobile fallback for the heavy effects.

## Themes
Two themes, circular-reveal transition (View Transitions API).

## Why it works
Every axis is pushed, but coherently — one mode set the ceiling, the aesthetic family set the character, hierarchy distributed the intensity so the page has loud and quiet passages. The 3D is part of the color system, not bolted on. This is the Active Theory / Igloo lineage approached honestly: code-buildable scene and materials, with assets sourced separately.
