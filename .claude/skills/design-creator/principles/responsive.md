# Responsive

## Approach

- **Design desktop → mobile**, but **write code mobile-first** (Tailwind-style).
- Responsive by default. A genuinely different component per screen is done **only on explicit user request**, not as a default.

## Six breakpoints of failure (check each)

1. **Grid → columns.** Multi-column collapses down; at 320px maximum one column.
2. **Navigation → burger.** Full nav collapses to a burger menu.
3. **Text / hero.** Fluid scaling (`clamp`) or stepped sizes — the hero must not overflow or shrink to nothing.
4. **Content + sidebar → stack.** Side-by-side becomes a vertical stack.
5. **Touch targets.** Minimum 44×44px.
6. **Overflow.** Ellipsis / word-break / flex-wrap. Test at 320px.

## Strange screens

Foldables, ultra-wide monitors, landscape orientation: the base responsive work above covers them reasonably. No separate effort is spent on them.

## Fluid engine — one system, not per-breakpoint patches

Drive type and spacing from a single fluid system rather than hand-tuning each breakpoint:
- A **modular scale**: pick a base size and a ratio (e.g. 1.2–1.333); every step is derived, not invented.
- Each step is a **`clamp(min, preferred-vw, max)`** so it interpolates smoothly between a mobile floor and a desktop ceiling — no sudden jumps at breakpoints, fewer CLS surprises.
- Spacing uses the same fluid tokens so type and rhythm scale together.
- Breakpoints then handle **layout structure** (column count, stack vs row), not value resets. This is the shared engine `typography.md` references.

## Status

- All six breakpoint checks: **MUSTHAVE-BASE**.
- Touch targets ≥ 44×44px: **MUSTHAVE-BASE**.
