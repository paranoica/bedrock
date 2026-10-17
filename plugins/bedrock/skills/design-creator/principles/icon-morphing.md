# Icon Morphing

SVG icon morphing — changing an icon to mean a change of state. Morphing serves meaning: the icon changes in sync with the state it represents.

## Three levels — take the simplest that works

**Level 1 — CSS morphing (transform).** Burger↔cross, plus↔cross, rotations. Covers ~70% of cases. The must-have for simple state changes. Pure `transform`, 60fps.

**Level 2 — stroke drawing (`stroke-dashoffset`).** A checkmark drawing itself, success ticks, completion moments. The path is drawn by animating the dash offset.

**Level 3 — path interpolation** via a JS library (flubber, GSAP MorphSVG) for *related* shapes. For shapes that are far apart, do not interpolate — cross-fade instead.

## Hard rule

`transition: d` on a path is **not reliable cross-browser** (animating the SVG `d` property works in Chromium and Safari but is unsupported in Firefox). Path interpolation always goes through a library or cross-fade.

## Hierarchy

Always reach for the simplest level that does the job. Do not interpolate paths when a CSS transform would do.

## Icon system

Project picks one stroke icon set as primary, one consistent weight and style. A second set is used only when forced (e.g. needing SVG path access for animation). One stroke set per project. The concrete set is a project decision — read it from the project's `CLAUDE.md` / rules, do not hard-code one here.

## Status

- Level 1 for simple state changes: **MUSTHAVE-DEFAULT**.
- Levels 2–3: **SITUATIONAL** — used where a completion/transition moment genuinely calls for it.
