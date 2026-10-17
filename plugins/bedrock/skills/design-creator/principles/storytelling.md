# Storytelling

## What storytelling means here

Storytelling on a page is **scroll-driven** — the page reveals, holds, swaps, and moves its content *as a function of scroll*, so that scrolling feels like being walked through something rather than paging past stacked boxes. It has two layers, and a real page uses both:

1. **The spine** — the order of sections is an argument: a beginning that opens a question, a middle that builds, a turn, a resolution. Sections cannot be freely reordered.
2. **The scroll mechanics** — the *techniques* that make that spine physically felt: pinning, sticky swaps, horizontal motion, scroll-tied transforms. This is what the visitor actually experiences as "this site tells a story".

A page that has neither is a flat brochure. A page that has only entrance-reveal on every section is **also** a flat brochure with fades — reveal alone is the floor, not storytelling. The mechanics below are what was missing when a layout "has no storytelling".

## The core scroll-storytelling techniques — USE THESE, not just reveal

These are the techniques that make scroll *narrative*. At least one substantial one belongs on any Statement page; Clean pages use the gentler ones. Do not default to plain section-reveal and stop there.

**Pin storytelling (pinned section).** A section locks to the viewport while the visitor keeps scrolling, and *inside* that held frame the content advances — steps change, a figure builds, captions swap, a number climbs. The scroll drives the content, not the page position. This is the strongest single storytelling device: the visitor scrolls and the *story* moves while the *frame* stays. Use it for a process, a transformation, a sequence of beats, the hook reveal.

**Sticky storytelling (sticky swap / two-track).** One element sticks (usually a visual, an image, a device, a diagram) while a column beside it scrolls normally. As the text passes, the stuck visual changes to match the paragraph being read. The relationship between the fixed track and the moving track *is* the narrative — the visual is always showing what the words are saying.

**Horizontal storytelling.** At a point in the vertical scroll, the page moves sideways instead — a gallery, a timeline, a sequence of chapters traversed left-to-right. Breaks the monotony of pure vertical and suits anything sequential.

**Scroll-tied transform.** A figure, 3D object, or graphic is rigged so its state is a direct function of scroll position — rotation, assembly, a path drawing, a fill. The visitor "operates" it by scrolling.

**Section-to-section continuity.** Sections do not just stack — they hand off: a shape from one section continues into the next, the background shifts on a gradient across several sections, an element travels down the page. The page reads as one continuous surface, not separate slabs.

Supporting/lighter techniques: scroll-reveal of sections (the baseline — always present, but never the whole story), light parallax, clip-mask reveal, word-by-word text reveal, scroll progress indicator, before/after swipe, number counter, background-color shift.

## The hero / fold — pick a scroll behaviour (the most-defaulted moment)

The first fold is where the median model is weakest: it ships a static hero with fade-in sections
below — a brochure. The mechanics above are *section-level*; the **hero's own behaviour as you
leave it** is a separate, deliberate decision. Every landing picks **one**, stated in the narrative:

- **Static + handoff** (Clean default) — the hero holds; the move is the *handoff*: the next
  section enters over it or pushes it out. Valid for Clean, but it must be a designed handoff
  (overlap / push / colour-carry), never a hard cut to a stacked block.
- **Sticky-overlay** — the hero pins (~100vh, `position: sticky`) while the next section scrolls
  up over it on a higher layer with its own background. Revealed, then covered. Native, cheap.
- **Scale-down / release** — past the fold the hero's focal element (oversized title / visual)
  scales down and fades, then releases as content enters (`animation-timeline: view()` or GSAP
  scrub). The fold compresses into the page.
- **Parallax-push** — the hero visual moves slower than the foreground (0.4–0.6×) and the next
  section pushes it out of frame. Depth at the fold.

Reduced-motion: the hero resolves to its composed static state and the next section sits plainly
below — designed, not stripped (`motion.md`).

## Section entrances — pick per section (not fade-everything)

A whole landing on one fade is the brochure tell — and now a measured one (it fails the gate's
`motion_non_inert`). Choose entrances per section from this menu. Trigger a little before centre
(~80% of viewport), 600–900ms, gentle ease, `transform`/`opacity` only:

| Entrance | What | Use on |
|---|---|---|
| Reveal (baseline) | fade + 24–48px rise | quiet / connective sections only |
| Stagger cascade | children enter in sequence, ~60–100ms apart | lists, card grids, feature rows |
| Count-up | numbers climb from 0 as they enter | stats / metrics |
| Clip-mask | content revealed by an expanding `clip-path` | a focal headline or image reveal |
| Word-rise | heading words rise out of a mask, staggered | the one statement headline |
| Parallax media | image/figure shifts at ~0.5× behind text | editorial / testimonial media |

Vary the entrance down the page (intensity-by-hierarchy): reveal is the *floor* between louder
beats, never the whole page. Same surprise/rhythm rules as below.

## How to choose

The **spine** decides which mechanics are used and where — pinning goes on the section that is a process or a build; sticky-swap goes where a visual must track an explanation; horizontal goes on a sequence. Pick deliberately against the spine. But the rule is firm: a Statement page that ships with only fade-in reveal and no pin / sticky / horizontal / scroll-tied moment **has no storytelling** and fails QA. "I labelled the sections Act 1..7" is not storytelling either — labels are not mechanics.

## Quality

- Reveal and all scroll motion are **unhurried** — ~600-900ms, gentle easing, triggered a little before centre, never a fast snap.
- One genuine **surprise moment** per page, at the narrative turn.
- Rhythm of density — dense, then air, then dense; tall, then short.
- Scroll-driven effects via proven libraries (a Lenis-class smooth-scroll, GSAP ScrollTrigger, drei ScrollControls for 3D) — never hand-rolled in production. In a single self-contained HTML demo a tidy `requestAnimationFrame` scroll handler is acceptable.
- All scroll motion respects `prefers-reduced-motion` (the page must remain fully readable with every section visible and static) and animates only `transform`/`opacity`.

## Native scroll-driven, then libraries

Light scroll reveals/parallax should use native CSS scroll-driven animations first (cheap, INP-friendly); escalate to a scroll library only for true pin/scrub/horizontal timelines. Tier the choice against the perf budget (`motion.md`, `perf-budget.md`).

## Go wide: a long landing carries SEVERAL beats, not one (the courage fix)

The most common timidity on a big editorial/brand/marketing landing is shipping **one** scroll
device (or worse, fade-only) down a short page. That is the median, and it fails ambition
(`ambition.md`). A wide Statement landing is a **sequence of distinct storytelling beats of
different kinds**, paced across the whole page:

- A flagship pinned beat (the process / transformation / hook reveal),
- a sticky two-track beat (a visual tracking an explanation),
- a horizontal beat (a gallery / timeline / chapters),
- a scroll-tied beat (a figure or path that the visitor "operates" by scrolling),
- with continuity carrying a shape/colour/element between them,
- and quieter reveal/parallax as connective tissue between the loud moments.

Vary the *type* — three pinned sections in a row is monotony, not richness. Pace by the
intensity-by-hierarchy rule: loud beat, breathe, loud beat. If the brief is expressive and the
page is long, **defaulting to a single device is a timidity fail** — propose the multi-beat
spine and justify down only for a concrete reason (perf budget, a deliberately minimal brief).
Reference-scout (`reference-scout.md`) is how you stock the vocabulary of what's possible
before deciding the spine.


> **Animated scroll is always on, and must never break layout.** The #1 way scroll/animation
> breaks a page is the containing-block trap (a `transform`/smooth-scroll wrapper capturing a
> fixed modal). Build per `principles/frontend-gotchas.md` (portal overlays out, native scroll
> first, opacity+transform only).

## The implementation stack (concrete)

Installed in the **project**, not the skill:

```bash
npm i gsap lenis        # the award-site default for scrubbed/pinned/scroll-tied work
# (Framer Motion is fine for UI hover/transitions; GSAP for timeline/scroll narrative.)
```

- **Lenis** — smooth scroll that is the single source of truth; it keeps WebGL and the DOM in
  sync and **restores native APIs like `position: sticky`** (essential for horizontal and
  sticky beats). Wire it to GSAP's ticker so ScrollTrigger reads lerped scroll.
- **GSAP ScrollTrigger** — `pin`, `scrub`, and timelines: the engine for every beat above.
  `SplitText` for word/line text reveals. **Never hand-roll pin/scrub in production** — it's
  brittle; a self-contained single-file demo may use a tidy `requestAnimationFrame` handler.
- For 3D-tied beats, scroll drives the R3F scene via drei `ScrollControls`/`useScroll` (`3d.md`).

## Recipe shorthands (the moves people ask for by name)

- **The "running line" that draws a path as you scroll** — an inline SVG `<path>` with
  `pathLength` normalized; animate `stroke-dashoffset` from full to 0 via ScrollTrigger `scrub`.
  The line draws itself along its route as the visitor scrolls. Cheap, striking, very common on
  award sites. Pair it with points that light up as the line reaches them.
- **Clip-path "fold" reveal** — reveal/swap a section by animating `clip-path` (an inset or
  polygon) on scrub; gives a theatrical fold instead of a plain fade.
- **Scrubbed shader/canvas reveal** — a WebGL plane whose uniform is tied to scroll progress
  (image dissolve, displacement, gradient flow) — the premium reveal (`3d.md` / OGL for light cases).
- **Pinned step-builder** — pin a frame, advance an internal index on scrub (steps, captions,
  a figure assembling, a number climbing).
- **Horizontal chapter track** — pin vertically, translate a wide row sideways on scrub; use
  `position: sticky` (via Lenis) so it stays put while the row moves.

All of these animate only `transform`/`opacity` (or GPU-cheap `clip-path`/`stroke-dashoffset`),
respect `prefers-reduced-motion` with a designed static alternate, and sit within the perf budget.

## Status

- A narrative spine, proposed to the user, every section justified against it: **MUSTHAVE-BASE**.
- At least one substantial scroll-storytelling mechanic (pin / sticky-swap / horizontal / scroll-tied) on a Statement page — reveal-only is a QA failure: **MUSTHAVE-BASE**.
- **The hero/fold has a chosen scroll behaviour** (sticky-overlay / scale-down-release / parallax-push / deliberate static-handoff) — a static hero with fade-in sections below is the brochure default and now fails the measured `motion_non_inert` check: **MUSTHAVE-DEFAULT**.
- **Section entrances are varied per section** (the menu above), not one fade down the whole page: **MUSTHAVE-DEFAULT**.
- **On a long expressive landing, MULTIPLE beats of different types (not one), paced by hierarchy** — a single-device long landing is a timidity fail: **MUSTHAVE-DEFAULT**.
- Unhurried timing, rhythm of density, one surprise moment, reduced-motion fallback: **MUSTHAVE-DEFAULT**.
- Which specific mechanics, and where: **chosen against the spine** — proposed in the narrative, approved by the user.
