# Performance budget

A site can be beautiful and unusable if it's heavy. The performance budget is an explicit axis the engine sets early and then enforces, so Statement ambitions don't quietly wreck Core Web Vitals.

## Set it as a survey question (default by archetype)

Ask the user, with sensible defaults proposed per archetype:

- **Lean** — utility, content, e-commerce where speed converts. Tight: minimal JS, no heavy 3D, CSS motion, native scroll effects. Default for commerce and pure-utility only.
- **Balanced** — **the default for brand sites, marketing, portfolios and product launches.** Moderate: targeted libraries, a real WebGL/canvas hero where it earns its place, scroll libs for the signature moment. This is the everyday default for expressive work, not a step up you have to justify.
- **Showcase** — portfolio/launch/brand moment where the experience *is* the product. Generous: heavy 3D, scroll-scrubbing, video — paid for knowingly.

If the user doesn't choose, take the archetype default and state it. **Do not reach for Lean "to be safe" on an expressive brief** — that pre-bans the signature moment before it's even proposed (`ambition.md`). Budget *for* one heavy hero moment; it's almost always affordable.

## The thresholds it protects (measured, `tools/verify.md`)

LCP < 2.5s, **INP < 200ms**, CLS < 0.1. INP is the one heavy JS and elaborate motion blow — it measures responsiveness across the whole session, so a Showcase budget must still keep the main thread free during interaction (`seo.md`).

## It gates Statement techniques

The budget is a real gate, not advice. Under **Lean**, the engine may not reach for: heavy WebGL/3D, scroll-scrubbing video, large animation libraries, big web-font families, autoplay video without a poster. But the gate runs in **one direction only**: it stops genuinely-too-heavy work — it is **not** a licence to default Lean and call it prudent. When a Statement technique the hook wants exceeds the budget, the engine **leads with the bold version and offers the lighter fallback** ("the hook is a scroll-scrubbed 3D build — that's the Balanced/Showcase version; here's the native-scroll fallback if you need Lean"), not the reverse. Propose bold, let the user dial down. Resolve true collisions by the precedence order in `governance.md`. A budget used to pre-justify timidity is a misuse of this file.

## Cheap-by-default substitutions

Prefer the light path that gets ~90% of the effect: native CSS scroll-driven animations over a scroll library for light reveal/parallax (`storytelling.md`); variable font over multiple files (`typography.md`); CSS transforms over JS animation; `content-visibility` and lazy-loading below the fold; a poster frame for video.

## Status

Perf budget set as an explicit axis (survey, archetype default), enforced against measured CWV, gating heavy techniques: **MUSTHAVE-DEFAULT**. The "Lean budget blocks heavy technique X" rule is **MUSTHAVE-BASE** once a Lean budget is chosen.
