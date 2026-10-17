"""stage.py — the Blender *stager* (not a modeller) for design-creator's baked-3D tier.

The thesis (see ``principles/3d-baked.md``): Blender here does **light, camera, material,
world, render and export** — the part that separates "looks intentional" from default-clay
slop. Geometry arrives from a recipe (procedural) or an imported GLB; this module never
free-form models an object.

Recipes build a mesh and hand it to :func:`finish`, which applies a material, rigs lighting,
frames the camera, configures Cycles, renders a still (and optionally a GLB), and writes a
``render-stats.json`` sidecar. The Node harness (``tools/blender-render.mjs``) reads those raw
stats and decides pass/fail — exactly the verify.mjs split: bpy *measures*, Node *judges*.

Conventions held on purpose:
* **data API over ``bpy.ops``** for scene construction (geometry via ``bmesh``, materials via
  node trees) — operators destabilise the view layer across versions. ``ops`` is used only for
  the render trigger and the glTF export, which have no data-API equivalent.
* every Principled input is set through :func:`_set_input`, which is a no-op when the input was
  renamed away in some Blender version — the recipe never hard-crashes on a version skew.

Run context: this module is imported *inside* Blender's bundled Python (``blender -b -P
recipe.py``), so ``bpy``/``bmesh``/``mathutils``/``numpy`` are always available here; it is not
importable from system Python.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import bmesh
import bpy
import numpy as np
from mathutils import Vector

# --- shared render defaults (the harness may override every one via params) -----------------
DEFAULTS: dict[str, Any] = {
    "res": 960,  # square preview by default; bump for ship renders
    "samples": 96,
    "device": "CPU",  # CPU is portable + deterministic; "GPU" needs configured Cycles prefs
    "seed": 0,
    "transparent": True,  # hero on alpha, to composite into the page
    "mode": "still",  # "loop" → also render a seamless 360° webm spin (non-interactive bg loop)
    "frames": 48,  # loop length; with fps=24 → a 2s loop
    "fps": 24,
    "material": "matte",
    "smooth": True,  # False → keep flat facets (crystals, low-poly)
    "accent": [0.55, 0.42, 0.98],  # linear RGB; recipes/harness pass the site accent here
    "glb": False,
    "view_transform": "AgX",  # Blender 5.x default; "Standard" for punchier flat color
    "world_strength": 0.6,
}


def params_from_argv(argv: list[str]) -> dict[str, Any]:
    """Parse ``-- --out <dir> --params <json>`` passed after Blender's ``--``.

    Args:
        argv: ``sys.argv``; everything before a literal ``--`` is Blender's own and ignored.

    Returns:
        A dict with ``out`` (Path) and the merged params (DEFAULTS overlaid by ``--params``).
    """
    rest = argv[argv.index("--") + 1 :] if "--" in argv else []
    out = ".design/3d"
    raw = "{}"
    i = 0
    while i < len(rest):
        if rest[i] == "--out" and i + 1 < len(rest):
            out = rest[i + 1]
            i += 2
        elif rest[i] == "--params" and i + 1 < len(rest):
            raw = rest[i + 1]
            i += 2
        else:
            i += 1
    params = {**DEFAULTS, **json.loads(raw)}
    params["out"] = Path(out)
    return params


# --- scene construction (data API) ----------------------------------------------------------
def reset() -> None:
    """Wipe the factory-startup scene to a clean slate (no default cube/camera/light)."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def mesh_from_bmesh(name: str, bm: "bmesh.types.BMesh") -> "bpy.types.Object":
    """Bake a ``bmesh`` into a linked scene object via the data API (no ``primitive_*`` op).

    Args:
        name: object + mesh datablock name.
        bm: the bmesh to write; it is freed here.

    Returns:
        The created, scene-linked object.
    """
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def shade_smooth(obj: "bpy.types.Object") -> None:
    """Mark all polygons smooth (data API; avoids the ``object.shade_smooth`` operator)."""
    for poly in obj.data.polygons:
        poly.use_smooth = True


# --- materials (the six from principles/3d.md, set defensively across versions) --------------
def _set_input(bsdf: "bpy.types.Node", name: str, value: Any) -> None:
    """Set a Principled BSDF input only if it exists (inputs get renamed between versions)."""
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value


def _principled(mat: "bpy.types.Material") -> "bpy.types.Node":
    mat.use_nodes = True
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def apply_material(obj: "bpy.types.Object", kind: str, accent: list[float]) -> str:
    """Attach one of the six material presets; returns the resolved kind actually applied.

    Args:
        obj: target object.
        kind: matte | metal | glass | emissive | iridescent | wireframe.
        accent: linear RGB used for emissive / iridescent / wireframe tinting.
    """
    mat = bpy.data.materials.new(f"{obj.name}_mat")
    a = (accent[0], accent[1], accent[2], 1.0)
    kind = kind if kind in {"matte", "metal", "glass", "emissive", "iridescent", "wireframe"} else "matte"

    if kind == "wireframe":
        # Emission wire over a transparent body — cheap "techno" accent.
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        emis = nt.nodes.new("ShaderNodeEmission")
        emis.inputs["Color"].default_value = a
        emis.inputs["Strength"].default_value = 2.5
        wire = nt.nodes.new("ShaderNodeWireframe")
        wire.inputs["Size"].default_value = 0.01
        transp = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(wire.outputs["Fac"], mix.inputs["Fac"])
        nt.links.new(transp.outputs["BSDF"], mix.inputs[1])
        nt.links.new(emis.outputs["Emission"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        mat.blend_method = "BLEND" if hasattr(mat, "blend_method") else mat.blend_method
        obj.data.materials.append(mat)
        return kind

    bsdf = _principled(mat)
    if kind == "matte":
        _set_input(bsdf, "Base Color", (0.78, 0.78, 0.80, 1.0))
        _set_input(bsdf, "Roughness", 0.62)
        _set_input(bsdf, "Metallic", 0.0)
    elif kind == "metal":
        _set_input(bsdf, "Base Color", (0.88, 0.88, 0.90, 1.0))
        _set_input(bsdf, "Metallic", 1.0)
        _set_input(bsdf, "Roughness", 0.18)
    elif kind == "glass":
        _set_input(bsdf, "Base Color", (1.0, 1.0, 1.0, 1.0))
        _set_input(bsdf, "Transmission Weight", 1.0)
        _set_input(bsdf, "Roughness", 0.04)
        _set_input(bsdf, "IOR", 1.45)
    elif kind == "emissive":
        # No compositor bloom (the headless Cycles glare is unreliable across the 4→5 rework — a
        # bloom halo belongs in the web layer / higher emission). Glow comes from the material.
        _set_input(bsdf, "Base Color", a)
        _set_input(bsdf, "Emission Color", a)
        _set_input(bsdf, "Emission Strength", 4.5)
        _set_input(bsdf, "Roughness", 0.4)
    elif kind == "iridescent":
        # Version-stable approximation: fresnel-driven hue shift into the coat, no reliance on a
        # specific "Iridescence"/"Thin Film" input that moved across releases.
        _set_input(bsdf, "Base Color", (0.05, 0.05, 0.07, 1.0))
        _set_input(bsdf, "Roughness", 0.12)
        _set_input(bsdf, "Metallic", 0.6)
        nt = mat.node_tree
        layer = nt.nodes.new("ShaderNodeLayerWeight")
        layer.inputs["Blend"].default_value = 0.4
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        cr = ramp.color_ramp
        cr.elements[0].color = (a[0], a[1] * 0.3, a[2], 1.0)
        cr.elements[1].color = (a[2], a[0], a[1], 1.0)
        nt.links.new(layer.outputs["Facing"], ramp.inputs["Fac"])
        if "Emission Color" in bsdf.inputs:
            nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
            _set_input(bsdf, "Emission Strength", 0.8)
    obj.data.materials.append(mat)
    return kind


# --- lighting, world, camera ----------------------------------------------------------------
def _aim(obj: "bpy.types.Object", target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def three_point(target: Vector | None = None, scale: float = 1.0) -> None:
    """Key / fill / rim area lights aimed at ``target`` — the matte-object workhorse rig."""
    target = target or Vector((0, 0, 0))
    rig = [
        ("key", 900.0, Vector((4, -4, 5)) * scale, 6.0),
        ("fill", 250.0, Vector((-5, -2, 2)) * scale, 9.0),
        ("rim", 700.0, Vector((0, 5, 4)) * scale, 4.0),
    ]
    for name, energy, loc, size in rig:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        bpy.context.scene.collection.objects.link(lo)
        _aim(lo, target)


def studio_world(strength: float, hdri: str | None = None) -> None:
    """A gradient studio world (or an HDRI when supplied) so metal/glass have something to reflect."""
    world = bpy.data.worlds.new("studio") if not bpy.context.scene.world else bpy.context.scene.world
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    if hdri and Path(hdri).exists():
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    else:
        coord = nt.nodes.new("ShaderNodeTexCoord")
        grad = nt.nodes.new("ShaderNodeTexGradient")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.03, 1.0)
        ramp.color_ramp.elements[1].color = (0.16, 0.16, 0.2, 1.0)
        nt.links.new(coord.outputs["Window"], grad.inputs["Vector"])
        nt.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def frame_camera(obj: "bpy.types.Object", lens: float = 55.0) -> "bpy.types.Object":
    """Place a three-quarter camera and fit it to the object's bounding sphere."""
    center = sum((obj.matrix_world @ Vector(c) for c in obj.bound_box), Vector()) / 8.0
    radius = max((obj.matrix_world @ Vector(c) - center).length for c in obj.bound_box)
    cd = bpy.data.cameras.new("camera")
    cd.lens = lens
    cam = bpy.data.objects.new("camera", cd)
    dist = radius * (lens / 18.0)  # empirical fit: comfortable framing with margin
    cam.location = center + Vector((dist * 0.8, -dist, dist * 0.65))
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    _aim(cam, center)
    return cam


# --- render, export, stats ------------------------------------------------------------------
def configure_render(params: dict[str, Any]) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU" if params["device"] == "GPU" else "CPU"
    scene.cycles.samples = int(params["samples"])
    scene.cycles.use_denoising = True
    scene.cycles.seed = int(params["seed"])
    res = int(params["res"])
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = bool(params["transparent"])
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = params["view_transform"]
    except TypeError:
        pass


def render_still(out_png: Path) -> float:
    """Render to ``out_png``; returns wall-clock render seconds."""
    bpy.context.scene.render.filepath = str(out_png)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


def export_glb(out_glb: Path) -> None:
    bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_visible=True)


def render_loop(out_dir: Path, frames: int, fps: int, obj: "bpy.types.Object") -> dict[str, Any]:
    """Render a seamless 360° spin of ``obj`` to a webm (VP9). Returns video info for the sidecar.

    A frame-change handler drives the spin instead of keyframes, sidestepping the action/fcurve API
    rework across Blender versions. The poster still (``render.png``, rendered by :func:`finish`)
    doubles as the no-WebGL / reduced-motion fallback image — the bake *is* the degradation rung.

    Args:
        out_dir: output directory; the webm lands here as ``model<start>-<end>.webm``.
        frames: loop length in frames (rotation completes exactly over the range → seamless).
        fps: frames per second.
        obj: the object to spin.
    """
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.fps = fps

    def _spin(sc: "bpy.types.Scene") -> None:  # frame_change_pre fires per frame during the render
        obj.rotation_euler = (0.0, 0.0, 2.0 * math.pi * (sc.frame_current - 1) / frames)

    bpy.app.handlers.frame_change_pre.append(_spin)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "WEBM"
    scene.render.ffmpeg.codec = "VP9"
    scene.render.filepath = str(out_dir / "model")
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    encode_s = time.time() - t0
    bpy.app.handlers.frame_change_pre.remove(_spin)
    produced = sorted(out_dir.glob("model*.webm"))
    webm = produced[-1] if produced else None
    return {
        "webm": str(webm) if webm else None,
        "frames": frames,
        "fps": fps,
        "duration_s": round(frames / fps, 2),
        "encode_seconds": round(encode_s, 2),
        "bytes": webm.stat().st_size if webm else 0,
    }


def _poly_count() -> int:
    return sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")


def write_stats(
    out_dir: Path, png: Path, glb: Path | None, render_s: float, recipe: str,
    video: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load the rendered PNG back and write raw stats the harness thresholds against.

    The harness decides pass/fail; here we only *measure*: alpha coverage (did anything render),
    luminance mean + stddev over the opaque region (flat fill ⇒ near-zero stddev ⇒ "black/empty"),
    poly count, render seconds, whether a GLB was written, and (loop mode) the webm video info.
    """
    img = bpy.data.images.load(str(png))
    buf = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(buf)
    rgba = buf.reshape(-1, 4)
    alpha = rgba[:, 3]
    coverage = float((alpha > 0.01).mean())
    lum = rgba[:, :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    opaque = lum[alpha > 0.01]
    stats = {
        "recipe": recipe,
        "png": str(png),
        "glb": str(glb) if glb else None,
        "alpha_coverage": coverage,
        "lum_mean": float(opaque.mean()) if opaque.size else 0.0,
        "lum_stddev": float(opaque.std()) if opaque.size else 0.0,
        "poly_count": _poly_count(),
        "render_seconds": round(render_s, 2),
        "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y],
        "video": video,
    }
    (out_dir / "render-stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def finish(obj: "bpy.types.Object", params: dict[str, Any], recipe: str) -> dict[str, Any]:
    """Stage an already-built object end to end: material → light → camera → render → export → stats.

    Args:
        obj: the geometry a recipe produced (or imported).
        params: merged params (see :func:`params_from_argv`).
        recipe: recipe name, recorded in the stats sidecar.

    Returns:
        The stats dict (also written to ``<out>/render-stats.json``).
    """
    out_dir: Path = params["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    if params.get("smooth", True):
        shade_smooth(obj)
    kind = apply_material(obj, params["material"], params["accent"])
    if kind in {"metal", "glass", "iridescent"}:
        studio_world(max(params["world_strength"], 0.8), params.get("hdri"))
    else:
        studio_world(params["world_strength"], params.get("hdri"))
    three_point(scale=1.0)
    frame_camera(obj)
    configure_render(params)
    png = out_dir / "render.png"
    render_s = render_still(png)  # poster frame — also the no-WebGL / reduced-motion fallback image
    video = None
    if params.get("mode") == "loop":
        video = render_loop(out_dir, int(params["frames"]), int(params["fps"]), obj)
    glb = None
    if params["glb"]:
        glb = out_dir / "model.glb"
        export_glb(glb)
    return write_stats(out_dir, png, glb, render_s, recipe, video)
