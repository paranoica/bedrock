# Pattern: Auth (sign-in / sign-up)

This file gives Claude what to assemble, not what to copy.

## 1. Purpose
Get the user in (or registered) with the least possible friction — the highest-stakes form on the product.

## 2. Block composition
**Required:** the input fields (email + password, or email-only / magic-link), a primary submit button, a switch between sign-in and sign-up.
**Optional:** social auth buttons, "forgot password", a remember-me toggle, a side panel with brand/visual, inline field validation.

## 3. Order logic
Brand mark → form heading → social auth (if any) → divider → fields → primary submit → secondary links (forgot password, switch mode). Social auth goes above the divider because it is the faster path; the manual form below it.

## 4. Variants by mode
- **Clean** — centered card, calm, minimal.
- **Statement** — a split layout (form + a brand/visual/3D panel), bolder type — but the form itself stays calm and frictionless regardless of mode.

## 5. Technique bindings
- Forms follow `principles/forms.md` — label-above, inline validation, concrete-reason errors, focus to first error.
- Submit button carries idle/loading/done states (`principles/motion.md`).
- Error state next to the field, light shake (`principles/forms.md`).
- A brand-side 3D/visual panel is optional (`principles/3d.md`, `principles/decorative-graphics.md`).
- `:focus-visible` and full keyboard operability are mandatory (`principles/accessibility.md`).

## 6. Typical mistakes
- Placeholder-as-label — the user forgets what a field was once typing.
- A vague "invalid credentials" with no actionable detail where detail is safe to give.
- Submit with no loading state — double submits, user uncertainty.
- Errors listed at the top instead of next to the field.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.
