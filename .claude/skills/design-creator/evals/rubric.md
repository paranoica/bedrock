# Eval rubric

Every line is yes/no. Map to invariants. A "no" on a brief whose `stresses` list names that rule is a regression.

## Universal (every brief)

- Hook is stated and realized (`concept.md`) — Y/N.
- Anti-slop floor holds: no Inter/Roboto display, no purple-default, no pure #000/#FFF, no default form controls, no emoji, no AI badge — Y/N.
- Accent ≤ ~10% unless family override is stated — Y/N.
- One light source; dark theme uses light-driven elevation, not inverted shadows — Y/N.
- Accessibility: focus-visible, contrast ≥ 4.5/3:1, targets ≥ 44px, semantic + heading hierarchy — Y/N.
- Reduced-motion resolves to a designed static state, not bare-off — Y/N.
- No fabricated testimonials/metrics/logos; placeholders marked — Y/N.
- Confidence flagged where a choice is a guess — Y/N.

## Deliverable-type correctness

- Gate applied the right branch (landing = full; app surface = skip Architecture & narrative; component = minimal) — Y/N.
- No scroll-storytelling spine demanded of an app surface/component — Y/N.

## Domain & taste

- Chosen family passes the domain-fit guard; mismatches surfaced, not shipped silently — Y/N.
- Learned taste applied as default and stated, never overriding the floor — Y/N.

## Existing project

- De-facto tokens read and obeyed; conform-guard blocks off-system values — Y/N.
- Existing component library restyled, not duplicated — Y/N.

## Performance & SEO (public pages)

- Perf budget set; heavy techniques within it or trade-off surfaced — Y/N.
- CWV thresholds met (measured) — Y/N.
- Head essentials + JSON-LD (matching DOM) + OG present; content in first HTML — Y/N.

## Verification honesty

- Measured checks actually rendered/measured, or labelled "requires render" — never self-attested — Y/N.

## Ambition calibration — restraint (negative briefs only: `negative: true`)

These briefs FAIL on over-ambition, the mirror image of the slop floor. A document-class or
utility surface that arrives with scroll spectacle, 3D, kinetic type, or statement-mode theatre
is wrong even if beautifully executed.

- The `anti_pattern` techniques for this brief are ABSENT — Y/N (a "no" = over-ambition FAIL).
- Restraint is intentional and still has a point of view: a signature in the quiet register
  (typographic rhythm, spacing system, interaction quality), not an absence of ideas — Y/N.
- Hierarchy and legibility are the dominant achievement, not decoration — Y/N.
- The engine did NOT invent a "hook" that fights the deliverable's job (a legal page's hook is
  clarity, not spectacle) — Y/N.
