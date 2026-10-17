# Motion

## Principle

Everything interactive reacts — without fanaticism. An interactive element that does not respond to interaction reads as broken. But motion serves meaning; motion for its own sake is noise.

## Character

- Default response is **fast and crisp: 120–180ms**. Expression scales with mode.
- **Hover and active always come together.** Never style hover without active.
- Animate only `transform` and `opacity` — 60fps.
- `prefers-reduced-motion` everywhere.
- Any indicator of an active state **moves animatedly** between positions — it never jumps.

The micro-level — how each individual element is finished (every icon, button, card, link given full idle/hover/active states) — lives in `interaction-detail.md` and is enforced by the QA gate in `design-qa.md`.

## Must-have motion (MUSTHAVE-DEFAULT)

- Stagger / cascade for lists.
- Number counter with digit substitution.
- Ripple wave on click.
- Accordion expand/collapse.
- Button border fill on hover.
- Link: color shift + underline that slides in.
- Hover state on form fields.
- Toast.
- Button with states (idle / loading / done).
- Skeleton (see `principles/skeletons.md`).
- Tabs with a sliding active indicator.

## Statement motion (STATEMENT)

- 3D tilt.
- Bouncing / jumping letters.
- Glossy sweep on text.
- Arrow that travels.
- Slide fill.
- Glow that follows the cursor.
- Card reveal-on-hover.

## Dropped — never use (DROPPED)

- Spring/bounce on buttons — reason: feels toy-like, undermines crisp response.
- Card lift on hover (`translateY` + shadow) — reason: overused, generic; the #1 slop tell. Cards must still react on hover — but via wash / border-shift / reveal / arrow, never a plain lift. See `interaction-detail.md`.
- Magnetic button — DROPPED **by default** because it's gimmicky and hurts targeting, not because "a user rejected it". This is a taste call, not a law: if the owner wants it, the engine asks/offers and applies it, and the preference is remembered per-owner (`taste-profile`, two-level: owner default + project override). Distinguish from the genuinely objective drops above (card-lift, spring) which stay banned on craft grounds.

## Focus — important

Do **not** remove focus. Use `:focus-visible`:
- `outline` is not visible by default (clean look for mouse users — they never see a ring).
- `:focus-visible` shows a brand-styled ring **only on keyboard navigation**.
- This is non-negotiable accessibility; it is also exactly the clean look a mouse user wants. See `principles/accessibility.md`.

`:focus-visible` is **MUSTHAVE-BASE** — never overridden.

## Reduced-motion is a designed alternate, not "off"

`prefers-reduced-motion: reduce` must resolve to a **composed static state**, not a stripped page. For every motion-bearing element, design the still version: the final composition the animation would have arrived at, with instant (or ~0ms) state changes and no parallax/auto-play. A scroll-reveal becomes "already revealed and well-placed"; a kinetic headline becomes its strongest static setting. The reduced-motion experience should look intentional, equal in quality to the animated one — never a visibly degraded fallback. (Cross-link: the degradation-ladder in `3d.md`/`decorative-graphics.md`.)

## Degradation ladder (heavy motion)

Any heavy motion declares its fallbacks: full → reduced-motion designed-static → low-GPU → touch → no-JS. Correct and on-brand at each rung (shared with `3d.md`, `decorative-graphics.md`).

## Native scroll-driven animation (tiered)

Prefer **native CSS scroll-driven animations** (`animation-timeline: scroll()/view()`) for light reveal and parallax — no library, cheap on the main thread, good for INP (Chromium + Safari; progressive-enhanced where unsupported). Reach for a scroll library (Lenis/GSAP ScrollTrigger) only for heavy pin/scrub/timeline work that native can't do. Match the tier to the perf budget (`perf-budget.md`).

> **Animated scroll is always on, and must never break layout.** The #1 way scroll/animation
> breaks a page is the containing-block trap (a `transform`/smooth-scroll wrapper capturing a
> fixed modal). Build per `principles/frontend-gotchas.md` (portal overlays out, native scroll
> first, opacity+transform only).
