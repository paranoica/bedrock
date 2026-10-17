# Optimization

## Principle

Optimization does not cut the user's wishes — it realizes them cleanly. The goal is "fast AND 60fps" achieved by technique, not by removing features.

## Four groups

**Loading.** Code splitting; fonts with `display: swap`; lazy-load heavy scripts.

**Render / 60fps.** Animate only `transform`/`opacity`; `will-change` used sparingly and pointed; virtualization for long lists.

**Media.** Responsive images (`next/image`-class); `priority` for the LCP image; explicit width/height to reserve space (no layout shift).

**Delivery.** Performance budgets as a CI gate.

## UX patterns

- **Optimistic UI** — for reversible local actions only. NOT for payment, booking, or any irreversible/critical action.
- `debounce` / `throttle` on frequent events.
- Preload on intent (hover/focus).
- Cache.
- All four data states handled (loading / empty / error / data).
- State preservation across navigation.

## Status

- 60fps discipline (transform/opacity only), no-layout-shift media, four data states: **MUSTHAVE-BASE**.
- Code splitting, lazy scripts, budgets, optimistic UI for reversible actions: **MUSTHAVE-DEFAULT**.
