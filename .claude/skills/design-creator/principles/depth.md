# Depth, light & material

Cheap UIs are flat or use one hard shadow; expensive ones imply a consistent light source. This module is how surfaces sit in space. Confirmed by eye in testing: the dark-mode half is its own design, not an inverted shadow.

## One light source, everywhere

Pick a light direction (almost always top, slightly front) and make **every** surface agree: shadows fall the same way, top edges catch a highlight, gradients lighten toward the light. Mixed light directions are an instant "assembled from parts" tell.

## Elevation as a shadow stack (light mode)

A real shadow is never one blurry box. Stack at least two layers from the same light:

- a tight **contact** shadow (small offset, small blur, low alpha) — anchors the element to the surface;
- a soft **ambient** shadow (larger offset, large blur, lower alpha) — the diffuse cast;
- optionally a **hairline** top border (very low-alpha light line) that catches the "rim light" on the top edge.

```
box-shadow:
  0 1px 1px rgba(0,0,0,.05),
  0 3px 6px rgba(0,0,0,.06),
  0 10px 22px rgba(0,0,0,.09);
border: .5px solid (very light hairline);
```

Define ~4–5 elevation steps (flat → raised → overlay → modal → popover) and use them as tokens; never hand-roll a shadow per component.

## Dark mode is its own design, not an inversion (MUSTHAVE-BASE)

Dark shadows are nearly invisible on dark surfaces (black on black). On dark themes, **elevation is carried by light, not shadow**:

- a higher surface is a **slightly lighter** tone than the one beneath it (elevation = lightness step, not shadow depth);
- a **top hairline** of low-alpha white (`inset 0 1px 0 rgba(255,255,255,.06)` and/or a `border-top: 1px solid rgba(255,255,255,.12)`) reads as a lit top edge;
- keep a faint ambient cast for separation, but don't rely on it.

Never produce a dark theme by inverting the light theme's shadows — design the dark elevation model explicitly. (`theming.md` cross-link.)

## Material

A surface can have material beyond flat fill, used sparingly and on purpose: subtle grain/noise to kill banding on large fills; a frosted/`backdrop-filter` layer for overlays and sticky bars (with a solid fallback); a single continuous gradient only where it conveys something (light falloff, depth) — never gradient-as-decoration. Interpolate gradients in Oklab to avoid the gray-dead middle (`color.md`).

## Status

One light source, multi-layer elevation tokens in light mode, light-driven elevation in dark mode, restrained material: **MUSTHAVE-DEFAULT**; "dark is its own design, not an inversion" is **MUSTHAVE-BASE** (recorded in `invariants.md` #4 and `theming.md`).
