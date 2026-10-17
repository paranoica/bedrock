# Cursor

Custom cursor and cursor-driven effects. All of these are **Statement-level, strictly on user request — never a default.** All fully **disabled on touch** (there is no cursor there). They must not lag (or only barely).

## The techniques

- **Dot cursor** — the system arrow replaced by a dot/ring that grows over interactive elements. The base of a custom cursor; a branded feel. Reaction to everything clickable is mandatory.
- **Trail** — a tail follows the cursor. Purely decorative, carries no function — strictly on request, only where playfulness fits. On a serious product: skip.
- **Element distortion** — an element tilts/deforms near the cursor (the same tilt as in motion, seen as a cursor effect). Dosed, weak force.

## Dropped — never use (DROPPED)

- **Magnetic zones** — DROPPED by default (gimmicky, hurts targeting). A taste call, not a law — offer/ask if the owner wants it; remember per-owner (`taste-profile`).
- **Contextual cursor** — DROPPED by default on the same taste grounds; available on explicit request.

## Hierarchy of justification

Decorative cursor effects (trail, distortion) are pure aesthetics — dose them hard. A bad implementation irritates more than no custom cursor at all; when in doubt, the normal cursor is not shameful.

## Status

- Dot cursor, trail, element distortion: **STATEMENT**, on user request, disabled on touch.
- Magnetic zones, contextual cursor: **DROPPED**.
