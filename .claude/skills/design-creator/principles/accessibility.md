# Accessibility

A dedicated system block. Accessibility is not optional polish — it is what lets people who cannot use a mouse, or cannot see well, use the product at all.

## Focus

- `outline` is not visible by default — a clean look; a mouse user never sees a focus ring.
- `:focus-visible` shows a **brand-styled focus ring only on keyboard navigation**.
- Never remove focus entirely. This is non-negotiable. `:focus-visible` is the compromise that gives a mouse user the clean look they want and a keyboard user the ring they physically need.

## Motion

- `prefers-reduced-motion` everywhere — it disables auto-rotation, scroll-velocity deformation, large/abrupt movement.
- Reduced-motion fallbacks are provided, not an afterthought.

## Contrast

- Body text ≥ 4.5:1; large text ≥ 3:1.
- Never rely on color alone to carry meaning — pair it with shape, icon, or text.

## Touch & input

- Touch targets ≥ 44×44px.
- Cursor-dependent effects degrade gracefully on touch.

## Semantics & keyboard

- Semantic HTML — real headings, landmarks, lists, buttons vs links used correctly.
- Full keyboard navigation — every interactive element reachable and operable by keyboard.
- Overlays trap focus while open and restore it on close.
- ARIA where semantics alone are insufficient — labels on icon-only buttons, roles where needed. ARIA is a supplement to semantic HTML, not a replacement.
- Screen-reader sanity: every meaningful image has a text alternative; decorative images are hidden from the reader.

## Reduced motion = a designed state

`prefers-reduced-motion: reduce` is not "animations off" — it is a deliberately composed static alternate of equal quality (see `motion.md`). Every motion-bearing element must have its still version designed, not stripped.

## Status

- The entire block — `:focus-visible`, `prefers-reduced-motion`, contrast, touch targets, semantics, keyboard, focus trap, ARIA basics: **MUSTHAVE-BASE**. Non-negotiable.
