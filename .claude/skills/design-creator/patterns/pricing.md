# Pattern: Pricing

This file gives Claude what to assemble, not what to copy.

## 1. Purpose
Let the visitor compare options and choose — with confidence, without friction.

## 2. Block composition
**Required:** a section heading, 2–4 plan units (each: name, price, what is included, a CTA).
**Optional:** a billing toggle (monthly/yearly), one "recommended" plan highlighted, a feature-comparison table, an FAQ link, a money-back / trust line.

## 3. Order logic
Heading → optional billing toggle → plan units left-to-right, usually ascending in price → optional comparison table below. The recommended plan is visually lifted (a badge, a stronger border, slight scale) so the eye is guided.

## 4. Variants by mode
- **Clean** — even plan cards, the recommended one subtly marked.
- **Statement** — bolder type, the recommended plan strongly distinguished, an animated billing toggle, counter animation on prices.

## 5. Technique bindings
- Billing toggle: smooth, the active state slides (`principles/motion.md`).
- Prices animate via the number counter (`principles/motion.md`).
- A comparison table follows `principles/data-viz.md` table rules.
- CTA buttons carry state (`principles/motion.md`).

## 6. Typical mistakes
- No plan highlighted — the user has no guidance.
- Prices that hard-swap on billing change instead of counter-animating.
- A comparison table styled as a raw browser table.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.
