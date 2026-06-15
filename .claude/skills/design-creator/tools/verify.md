# Verify — make the QA gate measured, not self-attested

The old failure: `design-qa.md` declared checks "binary" and "physically blocked", but with no reference and no rendering, the engine was really *grading its own code by reading it*. Several gate checks are runtime facts that cannot be read off source — text contrast over a photo/blur/3D glow, overflow at 320px, layout shift on load, INP. This module gives the gate real eyes.

The principle: **anything the gate states as a number, this module measures by rendering. Anything it can't measure here, it labels "requires render" instead of pretending it's binary.**

## When this runs

Inside the design-QA gate (`design-qa.md`), for every generation step, across **both themes** and the breakpoints `{320, 768, 1280}`. It is part of the gate, not an optional audit.

## What it produces

1. **Screenshots** — one per section × theme × breakpoint. The engine then *looks at the PNGs* (the same way you'd scrub a video frame by frame), not at the code. This is also how the user is shown the mockup at Gate 1 — the screenshot is the artifact they approve.
2. **Numbers** — accessibility, layout, and performance metrics from real tooling.
3. **Motion facts** — a scripted-scroll pass measuring `motion_non_inert` (the page actually moves on
   scroll — the hook is not inert), `scroll_jank` (longtask budget during the scroll),
   `reduced_motion_respected` (the motion collapses under `prefers-reduced-motion`), and for a webgl
   `<canvas>` the `webgl_render_loop_paused` + an approximate `webgl_script_budget`. These convert
   design-qa's "hook enacted", the reduced-motion rule, and the 3D perf discipline from Tier-3
   judgment to measured facts in the same hash-bound report (`report.motion` + `measured[]`;
   advisory/3D-budget + mockup-fidelity in `advisory[]`).

## Tooling (environment-dependent — degrade gracefully)

This needs a headless browser. Pick what the environment allows; if none is available, say so and fall back to "requires render" labels rather than faking a pass.

- **Headless render + screenshots**: Playwright (preferred) or Puppeteer driving headless Chromium. Load the page (a local preview server, or the static HTML/mockup file), set the viewport, set `prefers-color-scheme`, screenshot full page and per-section.
- **Accessibility numbers**: `axe-core` injected into the page → contrast failures, missing labels, ARIA/semantics issues, focus problems. This turns "contrast ≥ 4.5:1" from a guess into a list of exact failing nodes.
- **Layout facts**: in-page checks — `document.scrollWidth > clientWidth` at 320px (overflow), a `PerformanceObserver` for `layout-shift` entries (CLS), `LCP`/`INP` from the performance APIs.
- **Performance / CWV**: Lighthouse (programmatic) or the Performance API for LCP/INP/CLS against the budget (`perf-budget.md`, when present): LCP < 2.5s, INP < 200ms, CLS < 0.1.

## The minimal recipe

```
1. Serve the build (preview server) or open the mockup file.
2. For theme in [light, dark]:
     set prefers-color-scheme = theme
     for width in [320, 768, 1280]:
       set viewport
       screenshot full page + each section
       run axe-core -> collect violations
       check scrollWidth vs clientWidth at 320 -> overflow?
       read layout-shift entries -> CLS
3. LOOK at every screenshot. Run the design-QA visual checks against the
   PIXELS (hierarchy, optical balance, hover states where capturable,
   slop tells), not against the source.
4. Read the numbers against the thresholds.
5. Any failure blocks. Fix silently, re-render, re-check. Loop until green.
```

## Three diff modes (unchanged from design-qa, now backed by real pixels)

- **A — Figma file exists**: verify numeric tokens (spacing, type, color) against the file.
- **B — reference screenshots exist**: regional visual diff against them (split the frame into zones; don't full-screen diff — background dominates and hides real bugs).
- **C — no reference (default)**: the rendered screenshots + the measured numbers ARE the standard. "Spec-perfect" here means: matches the committed token contract (`.design/tokens.json`) and clears every measured threshold.

## Honesty rules

- If no headless browser is available in this environment, do **not** report measured checks as passed. Label them "requires render — not verified here" and tell the user how to run it (or that a render step is needed before ship).
- The mockup (Stage 1) must be built on the token scale so the screenshots and the extracted token contract agree. A mockup full of ad-hoc values makes the bridge lossy.
- Optical adjustments (`optical.md`) are exactly the kind of thing only visible in the rendered frame — this is one of the strongest reasons the gate renders rather than reads.

## The bundled script (this is now real, not a recipe)

`tools/verify.mjs` implements the recipe above with Playwright + axe-core. One-time setup:
`npm i -D playwright axe-core && npx playwright install chromium`. Run it on the build or
the mockup file:

```
node tools/verify.mjs <url|file.html> --out .design/verify \
  [--deliverable landing|app|component] [--mockup <approved-mockup.html>]
```

`--deliverable` (default `landing`) gates `motion_non_inert` — blocking for a landing, advisory for
an app surface / component. `--mockup` adds the advisory **structural fidelity** check (build vs the
approved mockup: section count + heading order — a non-blocking drift signal, since the mockup is
rough by design).

It writes `.design/verify/verify-report.json` + screenshots and exits `0` (measured pass),
`1` (measured fail), or `3` (no browser). See `tools/USAGE.md`.

## How the gate reads the report (the teeth)

The gate does **not** trust a narrated "I checked it". It reads `verify-report.json` and the
green condition is a fact about that file:

1. **Freshness binding.** The report carries `build_hash` (a hash of the build). If it doesn't
   match the current build, the report is **stale** → the gate is not green. This kills "I ran
   it earlier, then edited three lines and still call it passed".
2. **Tiers, explicit.** `measured` (axe serious/critical, 320px overflow, CLS, LCP, **and the
   motion pass** — `scroll_jank`, `motion_non_inert`, `reduced_motion_respected`,
   `webgl_render_loop_paused` — the script decides, binary) · `visual_required` (what only eyes can
   judge: hierarchy, optical balance, hook *quality*, slop tells, ambition; plus contrast axe marked
   *incomplete* = text over photo/gradient) · `advisory` (non-blocking signals: `webgl_script_budget`,
   `mockup_fidelity`) · `unverified` (no browser). **`MEASURED_PASS` is NOT "gate green"** — the
   `visual_required` list must still be done against the PNGs before the result ships.
3. **No eyes ⇒ never all-green.** A report with `browser: false` and zero `unverified` is a
   contradiction the gate rejects. You cannot claim everything passed without rendering.

## Status

The render-and-look loop, axe/CWV numbers in the gate, both themes and all breakpoints, the
honesty fallback, and reading the hash-bound `verify-report.json`: **MUSTHAVE-BASE** wherever a
headless browser is available. Where it isn't, the "requires render" labelling is itself
mandatory — silently self-attesting a measured check is a defect.
