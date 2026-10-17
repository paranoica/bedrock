# 3D — baked (offline Blender tier)

The offline-render sibling of `3d.md`. `3d.md` owns **live** 3D in the browser (React Three
Fiber). This file owns **baked** 3D: geometry and light rendered offline in headless Blender,
shipped as flat assets (PNG/EXR, webm/mp4) or as an optimised **GLB** the live R3F layer loads.

> **Lazy-loaded.** Pull this file **only** when the survey routes a 3D request to the *baked*
> branch (Q4 production method). Most 3D stays in the browser — do not load this by default.

## The one decision that governs everything: browser vs baked

Blender is **not** the default for "3D on a landing". The live R3F layer (`3d.md`) is. Reach for
baked only when an objective signal lands in the right column — when in doubt, **browser**.

| The request… | Route | Why |
| --- | --- | --- |
| Interactive / cursor-reactive / scroll-bound hero | **Browser R3F** (`3d.md`) | Blender bakes dead geometry; only live WebGL reacts |
| Mesh-gradient / shader field / animated blob, interactive | **Browser shader** (`3d.md`) | This is a fragment shader on a plane, never a Blender render |
| Static cinematic hero, path-traced look (GI, caustics, soft shadows) | **Baked → PNG/EXR** | Offline quality realtime WebGL can't match |
| Looping, non-interactive background | **Baked → webm/mp4** | Cheaper + better than a heavy always-on R3F loop |
| A specific concrete object is required | text/image-to-3D (Meshy/Rodin) → **Baked stages the GLB** → R3F | Blender is the stager, never the modeller (below) |
| Procedural geometry too heavy for realtime | **Baked → GLB / texture maps** → R3F loads cheap | Move the cost offline; ship a light asset |

If the route is "Browser", close this file and use `3d.md`. Everything below assumes "Baked".

## Blender is a stager, not a modeller (the load-bearing rule)

The engine **never** free-form models a recognizable object in Blender by script — sculpting
topology blind, with a slow render as the only feedback, is where quality dies. Blender here does
the part that separates *looks intentional* from *default-clay slop*: **light, camera, material,
world, composition, render, export, optimisation.** Geometry arrives only two ways:

1. **Procedural** — a parametric recipe builds it in code (the green zone: blobs, crystals,
   displacement fields, scatter, wireframe forms). This is `tools/blender/recipes/`.
2. **Imported** — a supplied or generated GLB (Meshy/Luma/Rodin, or a CC0 model). Blender stages
   and optimises it; it does not author it.

A concrete recognizable object with no supplied/generated model → say so honestly ("this needs a
model"), exactly as `3d.md`'s asset pipeline does. Never lather a surrogate from primitives.

## Recipes are a generative space, not a preset library

The recipe vocabulary is the design language of this tier — and it must stay a **space of
parameters with wide range**, never a set of fixed looks. A preset library produces generic 3D —
the same `anti-slop.md`/`diversity.md` failure mode as a fixed web aesthetic. Each recipe exposes
`seed` + shape params (`amp`, `noise_scale`, `irregularity`, `elongation`, `facets`, …) precisely
so best-of-N / `spread.mjs` sampling gets real variety. When you add a recipe, add **range**, not
a style. (Spread wiring: pass the assigned cell's character into recipe params; see
`tools/blender/recipes/registry.json`.)

## The harness (measured, not self-attested — mirrors verify.mjs)

`tools/blender-render.mjs` is the baked sibling of `verify.mjs`. Node orchestrates Blender (as it
orchestrates Playwright); the bpy recipe + `tools/blender/lib/stage.py` do the in-engine work.

```
node tools/blender-render.mjs <recipe.py> --out .design/3d \
  --params '{"material":"glass","seed":7,"res":1200,"samples":192,"glb":true}' \
  [--blender blender] [--poly-budget 250000]
```

It emits a **hash-bound** `.design/3d/render-report.json` (`scene_hash` = sha256 of recipe +
`stage.py` + params; a stale hash is rejected at the gate, same as verify's `build_hash`). Tiers,
deliberately the same shape as verify:

- **measured** (binary, script decides, blocking): `render_succeeded`, `not_black` (alpha coverage
  + luminance stddev — catches a black/empty/flat-fill frame), `poly_budget`, and `glb_valid`
  *when* a validator is installed.
- **visual_required** (the critic must LOOK): `visual_3d_qa` — judge the render PNG against the
  exemplar (below), never in a vacuum.
- **advisory** (non-blocking): `render_time`; `glb_valid` downgraded to UNVERIFIED when no
  gltf-validator is on PATH.
- **unverified**: no Blender on PATH → exit 3, asset labelled "requires render", **never green**
  (fall back to browser R3F or an honest placeholder). Mirrors verify's no-browser honesty.

Exit codes: `0` measured pass · `1` measured fail · `3` no Blender.

## The critic judges baked 3D against an exemplar (weakest-axis discipline)

The render PNG goes to the **same** fresh-context critic (`tools/critic.md`, Tier 2). The model's
spatial/material taste is its **weakest** perceptual axis — so the baked-3D check is explicitly
**compare-to-reference**: judge against `references/3d-render-exemplar.md`, not from a blank slate.
On low confidence the critic returns `UNVERIFIED` and recommends an owner vote rather than forcing
a verdict — the same escalation `critic.md` already uses for the ambition axis.

## Degradation: the bake *is* the fallback (free synergy)

The degradation ladder in `3d.md` requires a designed static fallback for no-WebGL /
reduced-motion. A baked render **is** that fallback — the same PNG serves as the hero image and as
the bottom rung. When the live layer is R3F, render a baked still of the same scene as the
`<noscript>` / reduced-motion / low-GPU image; nothing extra to design.

## Maintainability (so the tier doesn't rot on the next Blender update)

- **Pin the Blender version** in the project and record it in `.design/journal.md` (the report
  records `blender_version`). Validated against **Blender 5.x**.
- **Data API over `bpy.ops`** for scene construction (geometry via `bmesh`, materials via node
  trees) — operators destabilise the view layer across versions. `stage.py` sets every Principled
  input defensively (a renamed input is skipped, not a crash). `ops` is used only for the render
  trigger and glTF export, which have no data-API equivalent.
- Every recipe calls `stage.reset()` first (factory-startup ships a default cube/camera/light).

## Licensing (same discipline as `3d.md`)

HDRIs, imported models, textures: CC0 / verified-permissive only, license + attribution recorded
in `.design/journal.md`. Fabricating a license is a `governance.md` violation. Generator output
(Meshy/Luma/Rodin) is a starting point with a stated quality ceiling, not a finished asset.

## Status

The baked tier is **SITUATIONAL** — proposed in the survey (Q4) and approved, never a silent
default. When it runs, the hash-bound harness report + the exemplar-anchored critic pass are
**MUSTHAVE** (a baked asset shown without them is self-attested). Where Blender is absent, the
"requires render" labelling is itself mandatory — silently claiming a render happened is a defect.
