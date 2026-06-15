# Frontend gotchas — failures that look fine in code and break at render

These are the bugs that don't show up by reading the source — they appear only when the page
actually renders, animates, and is scrolled on a real device. The engine **prevents them by
construction** (this file) AND the QA gate **catches them at render** (`tools/verify.mjs`
screenshots {light,dark}×{320,768,1280} and measures overflow/CLS). Both layers are required;
neither alone is enough. Most of these were learned the hard way in production — treat them as
settled, not optional.

## Cardinal rule: animated scroll is ALWAYS present — and it must NEVER break layout

Every page ships with **scroll-linked animation** (reveals, parallax, a scroll-tied beat — see
`storytelling.md`). That is non-negotiable. But "always animated" is worthless if the animation
breaks positioning — and the #1 way that happens is the containing-block trap below. So the rule
is two-sided: **scroll animation is always on, and it is implemented so that no overlay, modal,
sticky element, or section ever gets mispositioned by it.** A page whose scroll animation breaks
a modal fails QA exactly like a page with no animation at all.

## #1 — `transform`/`filter`/`perspective` on an ancestor breaks `position: fixed`/`sticky`

**This is the cause of "animated scroll + modal breaks the whole layout."** Per spec, any
ancestor with `transform`, `filter`, `perspective`, `backdrop-filter`, `will-change: transform`,
or `contain: paint/layout` (anything other than `none`) becomes the **containing block** for its
`position: fixed` descendants. The fixed element then positions relative to *that ancestor*, not
the viewport — so a modal/toast/dropdown rendered inside an animated or smooth-scroll wrapper
appears in the wrong place, gets clipped, or scrolls away. **Even an identity transform
(`translateZ(0)`, `scale(1)`) triggers it.** Sticky is hit too: a `transform` between the sticky
element and its scroll container distorts the stick.

This is *guaranteed* to bite when a JS smooth-scroll lib (Lenis/Locomotive) wraps the document in
a transformed container, or when an animated section contains a fixed overlay.

**Rules:**
- **Portal every fixed overlay to `<body>`** (modals, toasts, dropdowns, command palettes,
  tooltips, sticky headers) so no animated/transformed ancestor can capture it. In React: a
  portal; in plain HTML: render it as a direct child of `<body>`, not inside a section.
- **Never wrap the whole document in a persistent transform** if it contains fixed UI. If using
  a transform-based smooth scroll, portal all fixed UI out of the transformed wrapper (modern
  Lenis drives native scroll and avoids this — prefer that mode).
- A "fixed" element that's actually positioning relative to a section is the tell — check
  ancestors for `transform`/`filter`/`will-change` first.
- The QA gate must render with a representative **modal/overlay open** when the page has one, and
  confirm it centers on the viewport at every breakpoint — this is the automated catch.

## #2 — `backdrop-filter: blur()` (the Chromium jitter + iOS jank)

- **Never animate the blur *value*.** Animating `backdrop-filter: blur(N)` per frame causes
  per-frame jitter on mobile Chromium (the project's noted bug 40175472). **Apply the blur at its
  target value permanently and animate `opacity` instead.**
- **iOS Safari:** `position: fixed` + `backdrop-filter` causes severe scroll jank (repaints the
  blurred region every scroll frame) — use `sticky` or an opaque fallback on touch.
- Keep blur radius small: **≤ ~10–20px on mobile**; above that, dropped frames. Max **1–2**
  backdrop-filter elements on screen at once (each forces a compositor layer; many fragment GPU
  memory).
- It needs a **partially transparent background** to show, and **both** `-webkit-backdrop-filter`
  and `backdrop-filter`. Beware: a transformed/`overflow:hidden` ancestor or a `will-change`
  ancestor creates a "backdrop root" that clips or changes *what* gets sampled — another reason
  to keep blurred overlays out of transformed wrappers (ties to #1).
- Low-power devices: drop blur entirely, solid-color fallback is fine.

## #3 — Icon flicker / morph glitch during animation

Paired stateful icons (eye/eye-off, play/pause, menu/close) **flicker or jump** when toggled if
the icon is **remounted** or its path is hard-swapped mid-transition, or if it sits on a layer
that re-rasterizes.
- **Morph** between paths when they're structurally compatible (e.g. flubber path interpolation);
  **cross-fade + scale** when they're not. Never hard-swap the element.
- Don't unmount/remount the icon on state change — toggle within a stable element.
- If the icon lives inside a promoted/clipped layer, don't also transform the icon itself (see #4
  and #5) — animate a wrapper.

## #4 — Element "jitter"/snap at the END of an animation

A transform animation that looks smooth can **snap by ~1px on its last frame**. Causes: the
compositor layer is removed when the animation ends (or `will-change` is dropped), forcing a
re-rasterization at integer pixels; or the final `translate` resolves to a fractional pixel; or a
non-`transform`/`opacity` property was animated and triggered a layout pass.
- **Animate only `transform` and `opacity`** (and GPU-cheap `clip-path`/`stroke-dashoffset`).
  Never animate `top/left/width/height/margin/filter:blur` for motion.
- Keep the element transform-based through to rest; don't abruptly remove `will-change` the
  instant the animation ends — let it settle, then remove.
- Prefer `translate3d`/`translateZ(0)` for promotion, and avoid landing on sub-pixel offsets
  (round the final transform if you control it).
- For spring/idle-return interactions (the Lusion cursor pattern), lerp toward the rest value and
  **snap to exact rest once within an epsilon**, then stop the loop — otherwise it micro-jitters
  forever near the target.

## #5 — Rounded-clip AA hairline on images (Chromium bug 71639)

`border-radius` + `overflow: hidden` on an image/`bg-cover` leaves a 1–2px anti-aliased hairline
along the curve on Chromium.
- Use the **`.photo-clip` pattern**: `mask-image: linear-gradient(#000,#000)` + `isolation:
  isolate` + `transform: translateZ(0)` promotes the element to an isolated compositor layer
  whose contents are clipped at composite time, bypassing the bug.
- **Wrap animated photo cards — don't animate the clipped element itself.** The promotion uses a
  transform; if Framer/GSAP also transforms the same element, it overrides the CSS transform and
  the layer flickers, re-exposing the hairline mid-animation. Put `photo-clip` + bg on an inner
  element, put the motion (`whileHover`/variants) on an outer wrapper.
- **Don't stack rounded clips** on the same subtree (a `photo-clip` parent + a `rounded-*` child
  with its own radius produces a misaligned 1px seam). Round once, on one layer; inner children
  get no `rounded-*`.
- Last resort (some Chromium builds, when a `filter`/`backdrop-filter` is also present): bake the
  rounded corners into the source image with no alpha, or use a server-side transform.

## #6 — Smooth scroll vs INP: "animated scroll always" ≠ "Lenis always"

This is a real, project-proven tension: one project ships Lenis (premium lerped scroll); another
**removed** Lenis deliberately because its second rAF loop wrecked INP on low-end phones — native
scroll was fine there. The rule:
- **Default to native CSS scroll-driven animation** (`animation-timeline: scroll()/view()`),
  `position: sticky`, and `scroll-snap` — cheap, INP-safe, no extra rAF loop. For React,
  `framer-motion`'s `useScroll` reads native scroll without a smooth-scroll lib.
- **Escalate to a JS smooth-scroll lib (Lenis-class) only** when the design genuinely needs
  lerped scroll synced with WebGL/scrubbed timelines, **and** the target audience isn't
  low-end/INP-critical. On a perf-critical or low-end-primary target, do **not** add it.
- If Lenis is used, drive native scroll (don't transform-wrap the document — see #1), sync it to
  the animation ticker as the single source of truth, and **pause it when a modal locks scroll**.
- Decide this against `perf-budget.md` and the brief's audience — never add a smooth-scroll lib by
  reflex.

## #7 — No perpetual `requestAnimationFrame` loop driving CSS

A rAF loop that writes style every frame murders INP and battery. Drive animation with CSS
transitions on a `data-state` attribute, the Web Animations API, or a library's compositor-based
engine. A one-shot rAF that **stops the instant the animation completes** is acceptable; a
perpetual loop is not.

## #8 — `will-change` discipline

`will-change: transform/opacity` promotes a layer and helps a known-imminent animation — but
overuse fragments GPU memory and *adds* jank. Apply it just before the animation (or on hover
intent), **remove it after**, and never blanket it across many elements. It's a scalpel, not a default.

## #9 — Modals, scroll-lock, focus

- **Body scroll-lock through one ref-counted helper** (a `useScrollLock`), never by toggling
  `document.body.style.overflow` directly — two modals open at once would otherwise leave the page
  frozen after the first closes. When locked, also pause any smooth-scroll lib.
- Every modal: `role="dialog"`, `aria-modal="true"`, closes on Escape and click-outside, **traps
  focus and returns it to the trigger** on close. Rendered via a portal to body (#1).
- In Next, `next/dynamic({ ssr: false })` for user-triggered modals isn't allowed in Server
  Components — wrap in a client component.

## #10 — Entrance animations: `opacity` + `transform` only

No `filter: blur()` in entrance variants — it drops below 60fps. Reveal with opacity + a small
translate; if a blur-in is the design, it's the rare exception, measured, and never on many
elements at once.

## #11 — Framework traps (React 19 / Framer / Tailwind v4 / Next 16)

These are version-current footguns (verify against the project's actual versions via context7/docs):
- **Framer `LazyMotion strict`:** always `m.*`, never `motion.*` — strict mode crashes at runtime
  on a leaked `motion.*`. Honour reduced-motion once via `MotionConfig reducedMotion="user"`.
- **React 19 compiler on:** don't add `memo`/`useMemo`/`useCallback` — the compiler memoizes;
  manual memo is noise. Keep `"use client"` at the leaf, not on `page.tsx`.
- **Tailwind v4:** theme tokens in `@theme {}`, arbitrary values use **parentheses**
  (`bg-(--my-color)`, not `bg-[--my-color]`).
- **`content-visibility: auto`** + `contain-intrinsic-size` on long below-the-fold sections to
  skip offscreen render cost — but **never on the hero/above-the-fold** (it re-layouts on scroll).
- **Images:** `next/image` always; `sizes` is **required** with `fill`; `priority` only on the LCP
  element; compress (AVIF/WebP), never ship a huge PNG.

## #12 — Reduced motion is a designed alternate, not an afterthought

`prefers-reduced-motion: reduce` must leave the page fully readable with every section visible and
static; scroll-tied/auto-moving effects collapse to opacity-only or to a designed still. A
technique whose reduced-motion state wasn't designed isn't finished (ties to `motion.md` and the
degradation ladders in `3d.md`/`storytelling.md`).

## Status

- The cardinal rule (animated scroll always present AND never breaks layout): **MUSTHAVE-BASE**,
  checked at the QA gate (`design-qa.md`) and by `tools/verify.mjs` (overflow/CLS + overlay
  position).
- #1 (containing-block trap → portal fixed overlays), #2 (backdrop-filter), #4 (end-of-anim
  jitter), #5 (rounded-clip), #9 (modal/scroll-lock/focus), #10 (opacity+transform entrances),
  #12 (reduced-motion): **MUSTHAVE-BASE** wherever the relevant technique is used.
- #3, #6, #7, #8, #11: **MUSTHAVE-DEFAULT** — apply unless a measured project reason overrides,
  and verify framework specifics against the project's real versions.
