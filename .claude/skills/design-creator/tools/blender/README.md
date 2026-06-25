# tools/blender — the baked-3D engine

Headless Blender as a **stager** for design-creator's baked-3D tier. Not a modeller. Read
`principles/3d-baked.md` for the route (browser vs baked) and `tools/blender-render.md` for the
gate contract. This README is operational only.

## Layout

```
blender/
├── lib/stage.py        # the stager: material, light, camera, world, render, GLB export, stats sidecar
├── recipes/            # parametric geometry — each a generative space (param ranges), not a preset
│   ├── blob.py         # organic noise-displaced sphere
│   ├── crystal.py      # faceted irregular gem / shard
│   └── registry.json   # recipe manifest + param ranges (spread.mjs seam)
└── README.md
```

The Node harness lives one level up at `tools/blender-render.mjs` (sibling of `verify.mjs`).

## Run

```
# from the design-creator skill root
node tools/blender-render.mjs tools/blender/recipes/blob.py --out .design/3d \
  --params '{"material":"glass","seed":7,"res":1200,"samples":192,"glb":true}'
```

Preview fast (`res:480, samples:32`), ship slow (`res:1200+, samples:192+`). The harness degrades
honestly: no Blender on PATH → exit 3, UNVERIFIED report, never a faked pass.

## Adding a recipe

1. New file in `recipes/`. First line of `main()`: `stage.reset()`.
2. Build geometry with `bmesh` (data API, **not** `bpy.ops.mesh.primitive_*`), hand the object to
   `stage.finish(obj, params, recipe="name")`.
3. Expose **ranges** (`seed` + shape params), not a fixed look — keep it a generative space.
4. Register it in `registry.json` with param ranges.

## Requirements

- **Blender 5.x** on PATH (recipes use Blender's bundled Python; no host pip installs).
- Optional: Khronos **gltf-validator** on PATH to gate GLB structural validity (else advisory).
