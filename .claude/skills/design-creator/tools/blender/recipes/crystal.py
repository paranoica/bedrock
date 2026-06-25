"""crystal.py — a faceted, irregular gem: the parametric hard-edged hero form.

A generative space (see ``principles/3d-baked.md``): ``seed``, ``irregularity``, ``elongation``
and ``facets`` sweep a family of crystals. Flat-shaded on purpose — facets are the look — so it
passes ``smooth: false`` to the stager. Pairs best with glass / metal / iridescent materials.

Run: ``blender -b -P recipes/crystal.py -- --out <dir> --params '{"material":"glass","seed":7}'``
Recipe params (on top of the shared render params in ``stage.DEFAULTS``):
    facets        int    icosphere subdivisions (0–1 = chunky, 2 = jewel) (default 1)
    irregularity  float  per-vertex radial jitter (default 0.25)
    elongation    float  Z stretch for a shard look (default 1.6)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import bmesh  # noqa: E402  (Blender-bundled; only importable inside Blender)
from mathutils import Vector, noise  # noqa: E402

import stage  # noqa: E402


def build(facets: int, irregularity: float, elongation: float, seed: int) -> "bmesh.types.BMesh":
    """Build an irregular faceted crystal from a low-subdivision icosphere.

    Args:
        facets: icosphere subdivisions (0–1 chunky, 2 jewel-like).
        irregularity: radial jitter per vertex (0 = regular solid).
        elongation: Z-axis stretch (1.0 = none; >1 = shard).
        seed: offsets the jitter field so each seed is a distinct crystal.

    Returns:
        The constructed bmesh.
    """
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=facets, radius=1.0)
    except TypeError:  # pre-4.0 used "diameter"
        bmesh.ops.create_icosphere(bm, subdivisions=facets, diameter=2.0)
    offset = Vector((seed * 0.61, seed * 1.93, seed * 3.17))
    for v in bm.verts:
        j = noise.noise(v.co * 1.7 + offset)  # ~[-1, 1]
        v.co += v.co.normalized() * (irregularity * j)
        v.co.z *= elongation
    return bm


def main() -> None:
    params = stage.params_from_argv(sys.argv)
    stage.reset()  # drop factory-startup's default cube/camera/light before building
    params["smooth"] = False  # a crystal is faceted by definition; use blob.py for smooth forms
    bm = build(
        facets=int(params.get("facets", 1)),
        irregularity=float(params.get("irregularity", 0.25)),
        elongation=float(params.get("elongation", 1.6)),
        seed=int(params["seed"]),
    )
    obj = stage.mesh_from_bmesh("crystal", bm)
    stats = stage.finish(obj, params, recipe="crystal")
    print("STAGE_STATS", stats)


if __name__ == "__main__":
    main()
