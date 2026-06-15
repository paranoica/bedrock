# Optical adjustments — the invisible 5%

The difference between "fine" and "made by someone who cares" is a layer of corrections the eye demands but the math doesn't give. None of this is a fixed pixel value — it's "align by visible mass, then check by eye on a shrunk copy". This is also one of the strongest reasons the QA gate **renders and looks** (`tools/verify.md`) rather than reading code: optical defects only exist in the rendered frame.

## The core principle

Center and align by **visible mass**, not by the bounding box. Shapes with uneven weight (triangles, glyphs with overhangs, icons with a tail) have a geometric center and an optical center that don't coincide. The eye reads mass; honor the eye.

**Method, every time:** center mathematically → step back → squint, or shrink to ~16px → nudge toward the "light" side until the mass sits balanced → stop the moment it starts to feel like it's drifting the other way (that overshoot is the tell). Never ship a fixed offset as a rule — the right value depends on shape, size, and container.

## The recurring cases (cues, not formulas)

- **Play triangle in a circle/button** — its mass is on the left, the point on the right is nearly weightless, so a math-centered triangle looks shoved left. Nudge right a few px (tiny — for a ~22px glyph it's ~3–4px; overshoot looks "way too right" fast).
- **Single glyph in an avatar/badge** — optical middle of most letters sits slightly above geometric middle; nudge up a hair.
- **Icons with a tail/overhang** — balance toward the opposite side of the heavy element.
- **Hanging punctuation** — pull quotes, bullets, and quote marks *out* into the margin so the text block's left edge reads straight (`hanging-punctuation` where supported, negative margin otherwise).
- **Optical sizing across icons** — icons sized to the same box look unequal; size to equal *visual* weight (a circle reads smaller than a square at identical box size — grow it slightly).
- **Overshoot on round shapes** — circles and triangles must slightly exceed the cap height of adjacent text to look the same size (the same correction type designers apply to `o` vs `x` in type).

## Type-level optical work (cross-links to typography.md)

- Trim heading line-height optically, not by ratio — large type needs tighter leading than the body ratio implies.
- Negative letter-spacing on large display sizes; positive on small caps / all-caps.
- Align punctuation and quotes to the text edge, not the glyph box.

## Status

Optical alignment, overshoot, hanging punctuation, optical sizing: **MUSTHAVE-DEFAULT** — applied as the finishing pass on every build, verified by looking at the rendered frame, never encoded as a fixed offset. The rule the engine carries is the *principle and the check*, not a number.
