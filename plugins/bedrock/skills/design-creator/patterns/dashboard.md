# Pattern: Dashboard

This file gives Claude what to assemble, not what to copy. A dashboard is an application surface, not a landing page — no scroll storytelling; the posture is the dataviz posture.

## 1. Purpose
Let a working user see state and act on it — metrics, charts, tables, controls in one operable surface.

## 2. Block composition
**Required:** a layout shell (sidebar/topbar + content area), metric cards, at least one chart or data table.
**Optional:** filters / date range, a detail panel or drawer, real-time indicators, an empty/error state per data region.

## 3. Order logic
Shell frames the surface → key metrics at the top (scanned first) → charts → detailed tables below. Most important / most glanced-at data highest. Each data region owns its own loading / empty / error state — a region fails locally, not the whole screen.

## 4. Variants by mode
Dashboards lean Clean structurally regardless of mode — clarity first. "Statement" here means richer motion and polish, not a louder layout. Everything is animated and alive (the dataviz posture), but the grid stays legible.

## 5. Technique bindings
- The whole dataviz posture — animated, detailed, live (`principles/data-viz.md`).
- Numbers animate via the counter (`principles/motion.md`).
- Tables follow the worked-table rules, not browser defaults (`principles/data-viz.md`).
- Skeletons per data region (`principles/skeletons.md`).
- Per-region screen states (`principles/screen-states.md`).
- A detail drawer slides from the right, obeys the overlay rule (`principles/micro-mechanics.md`).

## 6. Typical mistakes
- A raw browser table dropped in as-is.
- One global loading state instead of per-region skeletons.
- Numbers that hard-swap instead of counter-animating.
- A dead, static dashboard — against the dataviz posture.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.
