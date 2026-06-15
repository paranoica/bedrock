# Micro-mechanics

The small interactive mechanics that hold a UI together.

## Smooth scroll

A Lenis-class smooth scroll (lerp ~0.08–0.12). Confirmed in the survey; respects `prefers-reduced-motion`.

## Overlays — the universal rule

Any overlay — modal, dropdown, popover, tooltip, drawer — **opens and closes smoothly, closes on outside-click and on Escape.** This is non-negotiable.

- Modals: appear with a Pop (spring) by default. Backdrop blur by default; sometimes dim + blur; sometimes no treatment — decided via the survey. `backdrop-filter` is heavy → mobile fallback.
- Drawer — slides from the right.

## Scrollbar

iOS-style overlay scrollbar: hidden → slides out on the right during scroll → retreats after 2–3s of rest.

## Page transitions

- Base must-have: fade + sometimes slide.
- Statement: content-cascade and curtain transitions.
- In the arsenal: circular-mask reveal via the View Transitions API.

## Cross-document View Transitions

Use the native View Transitions API — including **cross-document** transitions (MPA, no SPA required) — for shared-element and page-to-page morphs. This is how the brand `signature.md` persists through navigation. Always behind progressive enhancement and `prefers-reduced-motion`.

## Status

- The universal overlay rule (smooth, outside-click, Escape): **MUSTHAVE-BASE**.
- Smooth scroll, base page transition (fade): **MUSTHAVE-DEFAULT**.
- Modal treatment choices, scrollbar style: **SITUATIONAL**.
- Content-cascade / curtain transitions: **STATEMENT**.
