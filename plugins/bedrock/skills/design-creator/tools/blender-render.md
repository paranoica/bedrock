# Blender render — make the baked-3D tier measured, not self-attested

The offline-render sibling of `verify.md`. Same principle: **anything the gate states about a
baked asset as a number, this module measures by actually rendering; anything it can't measure, it
labels "requires render" instead of pretending.** It gives the baked-3D gate real eyes the same
way `verify.mjs` gives the web gate real eyes.

Read this only on the **baked** 3D branch (see `principles/3d-baked.md`). Live browser 3D is
`3d.md` + `verify.mjs`.

## When this runs

When the survey routed a 3D request to the baked tier and a recipe (or imported GLB) has produced
a render. It is part of the 3D QA gate, not an optional audit — a baked asset shown to the user
without a fresh hash-bound report is self-attested.

## What it produces

1. **A render** — `.design/3d/render.png` (RGBA, transparent film by default so it composites
   into the page). The engine then *looks at the PNG*, the same as the web visual tier.
2. **A stats sidecar** — `render-stats.json`, written by `stage.py` from inside Blender: alpha
   coverage, luminance mean + stddev, poly count, render seconds, resolution. bpy *measures*;
   the Node harness *decides* — the same split as verify (in-page JS measures, Node thresholds).
3. **Optionally a GLB** — `model.glb` when `--params '{"glb":true}'`, for the live R3F layer.
4. **A verdict** — `render-report.json`, the machine-readable result the gate/critic read.

## Tooling (environment-dependent — degrade gracefully)

Needs **Blender on PATH** (validated against Blender 5.x). Recipes run in Blender's bundled Python
(bpy/bmesh/numpy are always present there). If Blender is absent, the harness exits `3` and writes
an UNVERIFIED report — it does **not** fake a pass; the engine falls back to browser R3F or an
honest placeholder. GLB structural validation needs the Khronos **gltf-validator** on PATH; when
it's absent the GLB check is downgraded to advisory UNVERIFIED, never silently passed.

## The command

```
node tools/blender-render.mjs <recipe.py> --out .design/3d \
  --params '<json>' [--blender blender] [--poly-budget 250000]
```

`--params` is forwarded to the recipe and merged over `stage.DEFAULTS`. Shared keys: `res`,
`samples`, `device` (`CPU`|`GPU`), `seed`, `material` (matte|metal|glass|emissive|iridescent|
wireframe), `accent` (linear RGB), `transparent`, `glb`, `smooth`, `mode` (`still`|`loop`),
`frames`, `fps`, `view_transform`, `world_strength`, `hdri`. Recipe-specific keys are documented in
each recipe's header.

Preview fast (`res:480, samples:32`), ship slow (`res:1200+, samples:192+`). Cycles is the engine
(built for independent per-frame rendering → built for automation); EEVEE headless needs
`xvfb-run` and is not the default.

## How the gate reads the report (the teeth)

Same discipline as verify — the gate reads the file, it does not trust a narrated "I rendered it":

1. **Freshness binding.** `scene_hash` = sha256(recipe + `stage.py` + canonical params). If it
   doesn't match the current inputs the report is **stale** → not green. Kills "I rendered it
   earlier, then changed a param and still call it passed".
2. **Tiers, explicit.** `measured` (`render_succeeded`, `not_black`, `poly_budget`, and
   `glb_valid` when a validator exists — script decides, binary) · `visual_required`
   (`visual_3d_qa` — the critic LOOKs at the PNG vs the exemplar) · `advisory` (`render_time`;
   `glb_valid` UNVERIFIED with no validator) · `unverified` (no Blender). **`MEASURED_PASS` is NOT
   "gate green"** — the visual check must still be done against the render.
3. **No Blender ⇒ never green.** `blender: false` → the asset is "requires render", and the engine
   must fall back (browser R3F / placeholder), never present a baked asset that was not produced.

## Status

The render-and-look loop, the hash-bound report, and the honesty fallback are **MUSTHAVE** on the
baked branch wherever Blender is available. Where it isn't, the "requires render" labelling is
itself mandatory — silently self-attesting a baked render is a defect, exactly as in `verify.md`.
