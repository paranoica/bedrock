# Reference: baked-3D render exemplar

The compare-to-reference anchor for the critic's baked-3D visual check (`tools/critic.md` §8b).
The model's spatial/material taste is its **weakest** axis — so a baked render is judged *against
this*, never from a blank slate. A demonstration of the bar, not a verbatim template.

## What "looks intentional" baked 3D is (the bar)

A gallery-tier baked hero reads as deliberate craft, the way Igloo / Active Theory / studio product
shots do — and the difference from slop is almost entirely **light + material + composition**, not
geometry:

- **Lighting is shaped, not flat.** A key/fill/rim rig (or an HDRI for metal/glass) gives the form
  a bright side, a soft shadow side, and a separating rim. You can see where the light is. A flat,
  evenly-lit object is the tell of "default viewport", not a render.
- **The material reads true.** Glass actually **refracts** (you see distortion + internal lobes +
  a caustic-ish highlight). Metal **reflects an environment** (a gradient/HDRI world — metal with
  nothing to reflect is just gray plastic). Emissive **glows from within** (a bloom halo, if wanted,
  is a web-layer / R3F postprocessing step — not baked here). Matte has honest
  soft falloff. The accent color is **carried into the material**, so the 3D is part of the
  palette, not bolted on.
- **Composition has intent.** The object sits with breathing room and a slight off-axis framing,
  silhouette legible against (usually transparent) film so it composites into the page. Not
  dead-center, not filling the frame edge to edge.
- **It's clean.** No fireflies / speckle (enough samples + denoise), no visible faceting where the
  surface should be smooth, no self-intersection or clipping, no stray default object in frame.

Worked references in this repo (preview-res, but the read is right): a **glass blob** — smooth,
refractive, internal lobes from displacement, a single bright highlight; a **faceted glass
crystal** — elongated, light bending through the facets, a legible gem silhouette. Both are the
parametric Stripe/Vercel-hero lineage: abstract, deliberate, not stock.

## The slop failure modes (FAIL on sight)

- **Default-clay.** Flat gray matte, even ambient light, no rim, no shadow direction — the "I took
  a screenshot of the viewport" look. The single most common baked-3D slop.
- **Dead material.** Metal or glass with no environment to reflect/refract → reads as gray plastic.
  Metal/glass without an HDRI or gradient world is unfinished, full stop.
- **Centered frame-filler.** Object dead-center, touching all four edges, no composition.
- **Noise / fireflies.** Bright speckle from too-few samples or no denoise — looks unfinished.
- **Baked-in default background.** A gray Blender-world background rendered into the PNG instead of
  transparent film (so it can't composite, and it screams "Blender default").
- **Geometry-as-spectacle with no light.** A clever procedural mesh shot flat — the geometry was
  the easy part; if the staging didn't happen, it's still slop.

## How the critic uses this

LOOK at `.design/3d/render.png`. For each axis above, is the render on the **bar** side or the
**slop** side? Lighting shaped? Material true to its kind? Composition intentional? Clean? On
palette? If it's clearly slop on any axis → FAIL with the axis named. If it's genuinely
borderline and you'd flip on re-derivation → `UNVERIFIED` + recommend an owner vote
(`tools/taste.mjs`), don't fake certainty on taste — exactly the ambition-axis discipline.
