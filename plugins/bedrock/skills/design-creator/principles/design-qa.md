# Design-QA

## Goal

**Spec-perfect, not pixel-perfect.** 1-to-1 with a design file is structurally unachievable (Figma's layout engine, the browser's renderer, font rendering, sub-pixel rounding all differ). Professionals ship spec-perfect: tokens match, spacing comes from the scale, hierarchy matches; pixel differences within 1-2px are ignored as noise.

## QA is a GATE, not a recommendation

This is the core of this file. Design-QA is **a hard gate inside the work loop, not an optional audit at the end.** The result of a generation step **cannot be shown to the user** until the gate passes. "Show the result" (work-loop step 6) is physically blocked until every blocking check below is green.

**The self-check is not enough on its own — it grades work the same context produced.** So the gate has two parts that must BOTH be green: (a) this checklist, run by the engine; and (b) an **independent critic** in a fresh context (`tools/critic.md`), spawned on every result (one section or more) via `Task(subagent_type: "general-purpose", …)` with the build, `.design/tokens.json`, the `verify.mjs` report, the hook, deliverable type, mode, and the matching exemplar. The critic re-derives the verdict without seeing the engine's reasoning, so it catches what self-attestation misses. Its `FAIL` is authoritative — the engine does not argue a finding back in without pointing at the exact screenshot/line that refutes it. No install: it's spawned from the bundled file, not registered in `~/.claude/agents/`.

The failure this prevents: the engine builds a real, good-looking section, leaves the interaction details at their defaults (icons that do not react, buttons that snap, cards that just lift), and shows it anyway. The rules against this already exist in `motion.md` and `interaction-detail.md` — the gate is what makes ignoring them impossible. Skipping the gate is itself a defect.

## Branch on deliverable type FIRST

Before running the checklist, classify the deliverable — the checks are not all universal. This stops the gate from demanding a scroll-storytelling spine from a login form (and stops it from being silently ignored when it does).

- **Landing / marketing page** → the full checklist applies, including the **Architecture & narrative** block.
- **App surface** (dashboard, auth, settings, profile, in-app screen) → run everything EXCEPT the **Architecture & narrative** block. App surfaces have no hook-driven spine, no scroll mechanic, no varied section heights by design (`patterns/dashboard.md` says so explicitly). Clarity and the dataviz posture replace storytelling. Demanding a pin section here is the defect.
- **Single component / small edit** → run only Structure, Accessibility, Interaction-detail, No-slop, Smoothness. Skip Architecture & narrative and the hook-in-section check.

If unsure which branch, ask — do not default to the landing branch and then "relax" failing checks (that relaxation is the anti-rationalization tripwire in `invariants.md`).

## The blocking checklist

Run **every** check in the applicable branch before showing any result. Each is binary — yes/no, no scoring. **Any "no" blocks the result.** Claude fixes the defect silently and re-runs the whole checklist. Loop until all green. Only then is the result shown.

**Measured vs read.** The checks tagged **[render]** below are runtime facts and are verified by actually rendering and measuring (`tools/verify.md` → the bundled `tools/verify.mjs`) — not by reading the source. The gate reads `.design/verify/verify-report.json`, and "green" is a fact about that file, not a narrated claim: (a) its `build_hash` must match the current build (a stale report does not count — this stops "I ran it earlier"); (b) `measured` checks must have zero `blocking_failures`; (c) every `visual_required` entry must be done by LOOKING at the screenshots, not the source — `MEASURED_PASS` alone is NOT a green gate. If no headless browser is available, the report is `UNVERIFIED`: label those checks "requires render — not verified" rather than self-attesting a pass. A report claiming all-green with `browser: false` is a contradiction — reject it. Contrast also has a **render-free pre-check** — `tools/contrast.mjs` computes WCAG ratios over `.design/tokens.json` at token-lock, so a sub-floor palette is fixed *before* building (layer 1), not merely caught by axe here. **The motion pass is `measured` too:** `scroll_jank`, `motion_non_inert` (landing), `reduced_motion_respected`, and — when a webgl canvas exists — `webgl_render_loop_paused` carry the same teeth (a `false` is a `blocking_failure`, read from `report.motion`). `advisory[]` entries (`webgl_script_budget`, `mockup_fidelity`) are signals, never gates.

**Structure & layout**
- Spacing values all come from the scale - yes/no.
- Token values (color, radius, type) match the committed token contract (`.design/tokens.json`) - yes/no.
- Visual hierarchy is present (the eye has an obvious first landing) - yes/no.
- **[render]** No overflow at 320px (`scrollWidth <= clientWidth`) - yes/no.
- **[render]** No layout shift on load / on async content arriving (CLS) - yes/no.
- **[render]** Scroll-linked animation is present and not inert — elements actually transform/fade across a scripted scroll (`verify.mjs` → `motion_non_inert`, landing); animated scroll is always on (`storytelling.md`) - yes/no.
- **[render]** That scroll animation breaks nothing: with a representative overlay open (modal/dropdown/toast, if the page has one), it centers on the viewport at every breakpoint and no fixed/sticky element is trapped by a transformed/smooth-scroll ancestor (`frontend-gotchas.md` #1) - yes/no.

**Accessibility**
- **[render]** Body text contrast >= 4.5:1, large text >= 3:1, measured over the real rendered background (photo/blur/glow included), via axe-core - yes/no.
- `:focus-visible` present on every interactive element - yes/no.
- Touch targets >= 44x44px - yes/no.
- **[render]** `prefers-reduced-motion` fallback exists for every animation — the motion measurably collapses under the preference (`verify.mjs` → `reduced_motion_respected`) - yes/no.

**The hook**
- The site's stated hook (`concept.md`) is actually realized in this section, **enacted not inert** — `verify.mjs` → `motion_non_inert` is the measured floor (the page demonstrably moves on scroll); whether the hook is *good* stays a judgment (critic Tier-3) - yes/no.

**Interaction detail - element by element** (per `interaction-detail.md`)
- Every button has idle + hover + active states, hover does something real (not just opacity) - yes/no.
- Every stateful icon (theme toggle, burger, chevron, expander) morphs or moves on interaction - yes/no.
- No card uses a plain hover-lift (`translateY` + shadow) - it is DROPPED; cards respond by wash / border / reveal / arrow instead - yes/no.
- Every link has a constructed hover (underline-slide or similar), not a bare color change - yes/no.
- Tabs / toggles / segmented controls move their active indicator (slide, never jump) - yes/no.
- Every state change (open/close, loading/done, theme swap, validation) animates rather than snaps - yes/no.
- All interaction transitions are crisp (120-180ms direct; 200-400ms reveals) and use `transform`/`opacity` only - yes/no.

**No-slop**
- No DROPPED technique present anywhere (card-lift, spring buttons, magnetic, etc.) - yes/no.
- The "tell test" passes: there is one memorable thing - yes/no.
- **Ambition** (`ambition.md` + `tools/ambition-check.md`): not a vibe call. Run the grounded procedure — Step 1 binary proxies (≥1 *named* signature device; focal technique-stack depth ≥2; non-default composition; hook *enacted* not inert; not a ledger repeat), then Step 2 pairwise vs the matching `references/` exemplar (anchored on those proxies, position-bias controlled, distractor-guarded so "more effects" ≠ "better"), then Step 3 a fresh-context re-judgment that must agree. Fail proxies 1/3/4, or below-tier, or unstable across passes → ambition FAIL ("clean and correct but forgettable" FAILS). On an expressive brief a Clean/Lean result must be justified by a concrete restraint reason; a restrained brief still needs a signature, intent, and an enacted hook in its quiet register. Report the verdict as judgment with its grounding (Step 5), never as a measured fact - yes/no.
- No AI status-badge anywhere (dot + bordered pill + mono-caps label) - it is BANNED in `anti-slop.md` - yes/no.

**Architecture & narrative** *(landing pages only — skip for app surfaces and components)*
- The page uses a consciously chosen archetype, not the defaulted nav->hero->strip->grid->cta skeleton (`page-architecture.md`) - yes/no.
- Across projects in this session, this archetype and this hook-mechanism are not a repeat of a previous one without reason - yes/no.
- The page has a stated narrative spine and every section advances it (`storytelling.md`) - not a flat brochure - yes/no.
- The page actually USES a substantial scroll-storytelling mechanic - pin / sticky-swap / horizontal / scroll-tied - not only fade-in reveal (`storytelling.md`) - yes/no. A Statement page with reveal-only FAILS.
- Section heights/density vary - no flat run of equal medium sections - yes/no.
- Entrance animations are unhurried (~600-900ms, gentle easing, not a fast snap) - yes/no.

**Smoothness - per element**
- Every property that differs between idle and hover/active/focus (`color`, `background`, `border-color`, `box-shadow`, `opacity`, `transform`) is listed in that element's `transition` - no bare snap - yes/no.
- No hover border / glow / shadow appears instantly - each eases in - yes/no.

## Three reference modes

- **Mode A - a Figma file exists.** Verify *numbers* from the file: spacing, tokens, component structure. Compare data, not pictures.
- **Mode B - reference screenshots exist.** Regional visual diff against the screenshots.
- **Mode C - no reference (default).** The rendered screenshots + the measured numbers (`tools/verify.md`) ARE the standard. "Spec-perfect" here means: matches the committed token contract (`.design/tokens.json`) and clears every measured threshold — not "looks internally consistent to me by reading the code".

When two binding rules collide during QA, resolve by the precedence order in `governance.md` (safety/a11y > hook/deliverable-type > family/mode > aesthetic preferences), and state the bend in the narrative — do not pick silently.

## Diff method

- **Regional, not full-screen.** A mobile frame is 70-80% background/padding; full-screen diff drowns real bugs in matching background. Split the frame into zones (header / content / footer / each card) and diff each.
- **Structural diff over pixel diff** where possible.
- Anti-aliasing tolerance 1-2px.

## Cycle

- The gate runs **automatically** inside every generation step - Claude is not asked permission to run it.
- Claude fixes defects silently and re-checks; it does not narrate the audit or list the fixes.
- **The result is not shown until the gate is fully green.**
- The gate runs across **all breakpoints** and **both themes** - a defect on mobile or in the second theme blocks the result exactly as a desktop defect does.
- A separate, deeper *final* audit of a whole page may additionally be offered to the user - but it never replaces the per-step gate.

## Adversarial critic pass

After the checklist is green, run a separate **critic** pass whose only job is to attack the result — a different stance from the builder, not the same agent nodding at its own work. The critic looks for: the slop tells the builder rationalized, the one memorable thing actually being absent, hierarchy that's weaker than claimed, motion that snaps, the "tell test" failing. Run 1–N critics in distinct roles (a visual-craft critic, an accessibility critic, a brand/signature critic) when the stakes justify it. If a code-review skill or `/code-review` is available in the environment, hook the critic to it so code-quality and design-quality are reviewed together. Critic findings re-enter the gate as defects and loop until clean.

## Discoverability-QA (for public pages)

For any public-facing page, additionally audit the findability layer (`seo.md`): SSR/content-in-first-HTML present? `<head>` essentials unique and complete? JSON-LD valid and matching the DOM? semantics/heading hierarchy clean? OG/X-card present? CWV within budget (measured)? image `alt` + dimensions? This is its own audit branch, parallel to the visual gate — a beautiful page that no crawler or AI can parse is an incomplete deliverable.

## Status

The QA gate - blocking, automatic, run every step, all checks binary, result withheld until green, all breakpoints / both themes, deliverable-type branch, [render]-backed measurement, adversarial critic, discoverability audit for public pages: **MUSTHAVE-BASE**. The gate cannot be skipped, deferred, or downgraded to advisory.


