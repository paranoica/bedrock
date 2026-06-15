# Photography

Photos are part of the composition and part of the design system.

## Base rules (always applied — technical hygiene)

- **Fixed aspect-ratio per photo type**, not "as it came": 1:1 avatars/grid, 4:3 content, 16:9 covers/video, 3:4 portraits. Mismatched ratios tear a grid. `aspect-ratio` also reserves space — no layout shift.
- **`object-fit: cover` always.** The photo fills its frame keeping proportions; the excess is cropped. Without cover the photo squashes and faces deform — the instant "cheap site" tell. `object-position` controls which part survives the crop (portraits — top).
- **Unified treatment / tone.** Photos from different sources are a patchwork; bring them to one look — a color overlay into the palette, or black-and-white/duotone, or unified color correction. For real photos of people, light correction only — keep people natural.
- **Real photos or initials-fallback** — no stock people.

## Discussed individually with the user

- **Hover on photos** (zoom inside a static frame — `overflow: hidden` required; caption reveal; b/w → color). Zoom modest (1.05–1.15), `transform`/`filter` only, no hover on touch.
- **Photo in composition** (layering, bleeding past a section edge, elements on top, photo-background with text — mandatory darkening under the text).

## Art direction (not just "good images")

Images are a designed system, not decoration dropped in:
- **One grade/tone across all imagery** — a consistent treatment (warmth, contrast, a duotone, a subtle unifying wash) so a page of photos reads as one shoot, not a stock grab-bag.
- **Crop as a decision** — choose the crop for composition and focal point; lead the eye (gaze direction, leading lines) toward the next beat (`composition.md`). Don't center-crop everything.
- **Image under text needs treatment** — scrim, gradient, or panel for legibility; never raw text on a busy frame.
- **Know when NOT to use a photo** — a strong type composition, a diagram, or generous negative space often beats a literal stock image. A decorative photo that says nothing is slop.
- **Image SEO/perf** — `alt`, explicit dimensions/aspect-ratio (CLS), responsive sources, `priority` on the LCP image (`seo.md`).

## Status

- Fixed aspect-ratio, `object-fit: cover`, unified treatment, real-photos/initials: **MUSTHAVE-BASE**.
- Hover effects, composition layering: **SITUATIONAL** — discussed with the user.
