"""blob.py — an organic noise-displaced sphere: the parametric soft-hero form.

This is a *generative space*, not a preset (see ``principles/3d-baked.md``): ``seed``, ``amp``,
``noise_scale`` and ``subdivisions`` sweep a wide family of blobs, so best-of-N / spread sampling
gets real variety instead of one fixed look. Geometry only; ``stage.finish`` does the staging.

Run: ``blender -b -P recipes/blob.py -- --out <dir> --params '{"material":"glass","seed":3}'``
Recipe params (on top of the shared render params in ``stage.DEFAULTS``):
    subdivisions  int   icosphere detail (default 4 ≈ 5k polys)
    amp           float displacement amount along the normal (default 0.35)
    noise_scale   float spatial frequency of the noise (default 1.1)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import bmesh  # noqa: E402  (Blender-bundled; only importable inside Blender)
from mathutils import Vector, noise  # noqa: E402

import stage  # noqa: E402


def build(subdivisions: int, amp: float, noise_scale: float, seed: int) -> "bmesh.types.BMesh":
    """Displace an icosphere by 3D value noise to make an organic blob.

    Args:
        subdivisions: icosphere subdivision level (higher = smoother, heavier).
        amp: peak displacement along each vertex normal.
        noise_scale: noise frequency; higher = more, smaller lobes.
        seed: offsets the noise field so each seed is a distinct blob.

    Returns:
        The constructed bmesh (caller hands it to ``stage.mesh_from_bmesh``).
    """
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=1.0)
    except TypeError:  # pre-4.0 used "diameter"
        bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, diameter=2.0)
    bm.normal_update()
    offset = Vector((seed * 1.37, seed * 2.71, seed * 0.93))
    for v in bm.verts:
        d = noise.noise(v.co * noise_scale + offset)  # ~[-1, 1]
        v.co += v.normal * (amp * d)
    return bm


def main() -> None:
    params = stage.params_from_argv(sys.argv)
    stage.reset()  # drop factory-startup's default cube/camera/light before building
    bm = build(
        subdivisions=int(params.get("subdivisions", 4)),
        amp=float(params.get("amp", 0.35)),
        noise_scale=float(params.get("noise_scale", 1.1)),
        seed=int(params["seed"]),
    )
    obj = stage.mesh_from_bmesh("blob", bm)
    stats = stage.finish(obj, params, recipe="blob")
    print("STAGE_STATS", stats)


if __name__ == "__main__":
    main()
