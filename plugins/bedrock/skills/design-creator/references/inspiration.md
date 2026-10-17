# Inspiration — the owner-curated reference pack

The owner-approved reference set, organized by what to steal and **when it applies**. Read by
`principles/reference-scout.md` (alongside `.design/refs/` for per-project drop-ins) to stock
the hook/signature vocabulary and to anchor the ambition pairwise check.

**These are pointers to learn *technique and structure* from — never a clone library.** Never
copy a site's markup, CSS, shader code, copy, images, models, or exact layout (see the
copyright line in `reference-scout.md`). You are learning the grammar to write your own
sentence. Cite the lineage in `.design/journal.md` when a reference informs a decision.

## When NOT to use these references (read this first)

References are for **expressive** briefs. They are the wrong input — and aping them is a
defect — when the brief is:
- a **utility / tool / dashboard / admin / internal app** → restraint, density, and speed win;
  award-site flourish is noise here. Use the *product-aesthetic* entries (Linear-class), not
  the landing/experience ones.
- **accessibility-first / grief / medical / legal / high-stress** → calm, legible, no spectacle.
- **content- or data-heavy** (docs, news, catalogs) → reading and scanning beat motion.
- **low-end-device / perf-critical / INP-sensitive target** (e.g. the Root-City pattern: native
  scroll, no smooth-scroll lib) → the heavy WebGL/smooth-scroll references do not transfer;
  take only their *structural* ideas, implemented natively.
- **SEO-critical with a tight crawl/LCP budget** → a full WebGL "experience" is the wrong call.
In all of these, the floors (a11y, perf, domain-fit, reduced-motion) outrank any reference, and
"it looked cool on Active Theory" is never a reason to ship something heavy or fragile.

## Which references for which brief (segmentation)

- **Brand / launch / hero-product, budget + 3D justified** → Active Theory, Igloo, Lusion,
  Unseen, Immersive Garden.
- **Agency / portfolio / creative, 2D cinematic** → Exo Ape, Akaru, Locomotive, Cuberto, Basement.
- **Type-led statement / editorial** → Obys (kinetic type), Pangram Pangram, Klim.
- **Narrative landing (multi-beat scroll storytelling)** → Akaru, Lusion, Active Theory.
- **App surface / dashboard / SaaS product UI** → Linear (inside the app), Vercel, Raycast,
  Resend, Clerk — dark, precise, restrained. NOT the experience sites.
- **Clean / precision marketing** → Stripe, Family.
- **Loading screen as a designed beat** → Igloo, Unseen, Akaru.
- **Custom cursor** → Cuberto, Dennis Snellenberg.
- **Opt-in interaction sound** → Phantom (see the sound note in `interaction-detail.md`).

---

## 3D / WebGL experiences

### Active Theory — activetheory.net
- **2D/3D:** 3D · **Family/mode:** experience · Statement
- **Signature device:** a whole-site WebGL world where sections transition as one continuous
  spatial move, not page jumps; bespoke navigation.
- **Steal (idea level):** section-to-section transitions that read as a single continuous
  surface (the "M3-clean" handoff the owner flagged); a cohesive world metaphor; the pacing of
  reveals.
- **Why it works:** continuity removes the "stack of slabs" feeling — the page becomes a place.
- **When:** flagship brand/experience with real budget and a justified 3D concept.
- **When NOT:** utility, content-heavy, low-end target, SEO-critical.
- **Watch-outs:** maximum perf/asset/time cost; mandatory reduced-motion + no-WebGL fallback.

### Igloo — igloo.inc
- **2D/3D:** 3D · Statement
- **Signature device:** crystalline glass product reveal (transmission material), scroll-driven;
  a flawless loading/intro sequence.
- **Steal:** the **loading screen as a designed first beat** (sets tone, hides asset load — never
  a bare spinner); glass-as-hero with one focal object.
- **Why it works:** the intro earns attention before the payload lands; the single glass object
  is a clear signature.
- **When:** product/launch with one hero object.
- **When NOT:** multi-product, utility, low-GPU primary audience.
- **Watch-outs:** transmission glass is GPU-heavy (1–2 per scene), needs an HDRI, mobile fallback.

### Lusion — lusion.co
- **2D/3D:** 3D (but take the *communication*, not the tech) · Statement
- **Signature device:** a scroll-tied hero character/object (the owner's Interstellar-vibe
  "cosmonaut") that the cursor can also nudge, and that **eases back to its rest pose when the
  user stops** — plus a continuous guiding line that threads the whole page.
- **Steal:** (a) the **through-line** that visually connects the page top to bottom (an SVG path
  that draws on scroll, or a literal element that travels); (b) a scroll-tied focal object the
  visitor can also push with the cursor and that **lerps/springs back to rest when idle**; (c)
  the overall smoothness and the sense the site is *communicating* with the user.
- **Why it works:** the idle-return makes it feel alive and responsive without demanding input;
  the line gives the eye a continuous path so the story never feels segmented.
- **When:** expressive brand/portfolio with a character or object to anchor.
- **When NOT:** utility, dense content, touch-primary without a fallback.
- **Watch-outs:** the cursor-drag + idle-return needs careful lerp/spring tuning or it jitters
  (`frontend-gotchas.md` on end-of-animation jitter); reduced-motion + touch fallbacks required.

### Unseen Studio — unseen.co
- **2D/3D:** 3D-lite / glass · Statement
- **Signature device:** a strong loading screen, then an Apple-style glass/refraction effect tied
  to scroll.
- **Steal:** the **glass/refraction reveal on scroll** (Apple "liquid glass" feel); the loading
  screen as a beat.
- **When:** premium product/editorial. **When NOT:** low-end, utility.
- **Watch-outs:** refraction/glass cost; needs a lighter fallback; keep blur radius sane on mobile.

### Immersive Garden — immersive-g.com
- **2D/3D:** 3D · Statement
- **Signature device:** 3D models that reveal by cursor, with refined, physical hover.
- **Steal:** **reveal-by-cursor** (a mask/displacement that follows the pointer to uncover 3D)
  and hover that feels weighted, not instant.
- **When:** showcase/portfolio on desktop. **When NOT:** touch-primary, utility.
- **Watch-outs:** mandatory touch/no-hover fallback; throttle raycasting (~30fps).

---

## 2D editorial / motion

### Exo Ape — exoape.com
- **Signature device:** cinematic imagery + buttery smooth scroll + restrained, luxe motion.
- **Steal:** image-led cinematic pacing; the **restraint** — craft over quantity of effects.
- **When:** brand/agency/luxury editorial. **When NOT:** data-heavy, utility.
- **Watch-outs:** heavy imagery → perf; lazy-load, compress, `next/image`, respect LCP.

### Obys — obys.agency
- **Signature device:** bold **kinetic typography** and brutalist-editorial, grid-breaking layout.
- **Steal:** kinetic type as the hero device; the expressive editorial format (huge type,
  asymmetry, deliberate negative space) — the "format to remember" the owner flagged.
- **When:** brand/portfolio/creative wanting a type-led statement.
- **When NOT:** enterprise/corporate, accessibility-first (giant kinetic type can hurt reading).
- **Watch-outs:** kinetic type must stay legible and collapse under reduced-motion.

### Cuberto — cuberto.com
- **Signature device:** slick gradient motion + a bespoke **custom cursor**.
- **Steal:** the custom cursor (magnetic / morphing / context-aware); gradient-rich, confident motion.
- **When:** agency/creative/product on desktop.
- **When NOT:** touch-primary (cursor is desktop-only) — and never hide the real pointer in a way
  that breaks affordance/a11y.
- **Watch-outs:** custom cursor needs a clean touch fallback and must not swallow focus/hover semantics.

### Basement Studio — basement.studio
- **Signature device:** playful, technical interactions; confident dark + type, dev-studio voice.
- **Steal:** playful but precise micro-interactions; assured dark composition.
- **When:** tech/dev/creative brand. **When NOT:** enterprise/utility.
- **Watch-outs:** don't let playfulness erode clarity or perf.

### Akaru — akaru.fr
- **Signature device:** one of the strongest **scroll storytellings** around, plus a designed
  loading screen. (Owner's high-priority pick.)
- **Steal:** the **multi-beat narrative spine** (varied beats paced across the page — exactly the
  `storytelling.md` "go wide" bar); loading screen as a beat.
- **When:** brand/portfolio/agency narrative landing. **When NOT:** utility, data-heavy.
- **Watch-outs:** storytelling needs a designed reduced-motion static alternate.

---

## Product / app-surface aesthetic (NOT landings)

### Linear — linear.app (take the INSIDE of the app)
- **Signature device:** refined **dark product UI** — restrained near-black neutrals + one
  accent, crisp typography, fast precise micro-interactions, keyboard-first.
- **Steal:** the dark app-surface system (palette, type, interaction feel) for **dashboards,
  SaaS UIs, admin panels** — NOT Linear's marketing landing.
- **When:** app surfaces, dashboards, internal tools, product UI.
- **When NOT:** warm/expressive marketing landings.
- **Watch-outs:** this is an **app-surface** ref; don't ape the landing. Pairs with `modes.md` Clean.

### Arc — arc.net · Framer — framer.com (added — "make it not look AI" benchmarks)
- arc.net — playful-but-premium product site with **custom illustration** and a distinct voice;
  framer.com — interaction polish and **type-as-art**. Use as anchors for *distinctive product
  marketing* that is unmistakably not template/AI output. Steal: the willingness to commit to one
  characterful idea and finish every detail. When NOT: utility/dashboards (use the Linear lane).

### Vercel · Raycast · Resend · Clerk (added — same lane as Linear)
- vercel.com, raycast.com, resend.com, clerk.com — crisp dark developer-product sites: tight
  type, precise motion, restrained palette, strong empty/loading states. Use as **dark product /
  dev-tool** anchors. Watch-outs: easy to drift into sameness — keep one real signature.

---

## Clean / precision marketing

### Stripe — stripe.com · Family — family.co
- Stripe: the benchmark for **Clean precision** — gradient hero, exact spacing, flawless perf;
  the right anchor when the brief wants calm authority. Family: playful, characterful product
  landing. **When:** clean/trust-led marketing. **When NOT:** when the brief wants a loud statement.

---

## Interaction / sound

### Phantom — phantom.land (take only the sound idea)
- **Steal:** **opt-in interaction sound.** Bundle many short CC0 UI sounds; expose a sound toggle
  (default OFF); when the user opts in, interactions (hover, click, section-enter) get subtle
  audio. See `interaction-detail.md`. **Never** autoplay; default off; respect a mute and
  reduced-motion; tiny files; CC0 sources (e.g. freesound.org filtered to CC0).
- **When:** playful/experiential brand, games, launches. **When NOT:** utility, focus-heavy,
  accessibility contexts.

---

## Added at discretion (matches the owner's revealed taste)

- **Aristide Benoist — aristidebenoist.com** · **Dennis Snellenberg — dennissnellenberg.com**
  — refined WebGL/transition portfolios + a tasteful custom cursor (cursor lane with Cuberto).
- **14islands — 14islands.com** — polished studio work bridging 2D editorial and WebGL.
- **Pangram Pangram — pangrampangram.com** · **Klim — klim.co.nz** — type-foundry sites; the
  reference for **type-led** layout (pairs with Obys for kinetic type).
These extend the lanes above; treat them as secondary anchors, not must-copies.

## Conclusions-only / lower priority (owner verdicts)

- **Resn — resn.co.nz:** take only the idea of playful **two-way site↔user communication**,
  nothing structural.
- **Bruno Simon — bruno-simon.com:** a fully-playable 3D portfolio is a novelty, **not a model
  for client work** — skip unless the brief literally wants a game/toy.
- **Locomotive — locomotive.ca:** well-made but base; a low-priority smooth-scroll/layout reference.
- **Spline (spline.design) / Codrops (tympanus.net/codrops):** nice clean 2D landings; Codrops
  *separately* stays the **technique well** (case studies with code) for `reference-scout`.
- **Rauno — rauno.me:** micro-interaction/detail craft reference (storytelling there is quiet).

## Skipped (owner said no — do not resurface as inspiration)

oimo.io · studiofreight.com / darkroom.engineering (as a *site* ref; Lenis-the-library still
stands) · antinomy.studio · emilkowal.ski.
