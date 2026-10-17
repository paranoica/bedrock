# Skeletons

Loading skeletons for async content. A skeleton always lives in a working application, never on a landing page.

## The three-step model

1. **Default skeleton** — generic shape shown immediately.
2. **Metadata-adapted skeleton** — refined once basic metadata is known (counts, rough sizes).
3. **Real content, 1-to-1** — no layout shift when the real content replaces the skeleton.

The skeleton's geometry must match the real content's geometry, so the swap causes zero layout shift.

## Animation

- **Shimmer + Pulse — must-have.** Pulse when there are many skeletons at once; shimmer for single/isolated skeletons.
- **Gradient drift — optional**, only if the palette allows it. SITUATIONAL.
- **Blink — forbidden.** DROPPED.
- **Static — fallback** under `prefers-reduced-motion`.

## Timing

- Minimum display ~300ms — a skeleton that flashes for 50ms is worse than none.
- Exact speed is confirmed in the survey.

## Status

- Skeleton presence for async content, three-step model, no layout shift: **MUSTHAVE-BASE**.
- Shimmer/pulse: **MUSTHAVE-DEFAULT**. Gradient drift: **SITUATIONAL**. Blink: **DROPPED**.
