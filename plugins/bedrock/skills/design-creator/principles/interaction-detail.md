# Interaction Detail

The micro-level. `motion.md` says *which* animations exist; this file says *how every single interactive element is finished* so nothing ships half-done. The recurring failure — icons that do not react, buttons that snap, states that jump — happens when a real element is built but its interaction is left at the default. This file makes "default" unacceptable.

## The rule

**Every interactive element is unfinished until it has all three:** an idle state, a hover state, and an active (press) state — and every transition between states animates. An element with only an idle state is a defect, not a minimalist choice. This is verified element-by-element in design-QA before the result is shown.

## Per-element checklist

**Buttons** — idle / hover / active all defined. Hover does something real: a fill that wipes in, a border that fills, a slide, a glow — not just an opacity nudge. Active gives a tactile press (`scale(.97)` or a 2px translate). Transition 120–180ms. A button that only changes opacity on hover is under-finished.

**Icons** — an icon tied to a state (theme toggle, menu, accordion, expander) **morphs or moves on interaction** — Level-1 CSS transform at minimum (rotate, cross-fade, path flip). A theme toggle rotates or swaps its glyph; a chevron rotates; a burger crosses. A static icon on an interactive control is a defect (`icon-morphing.md`).

**Cards** — a card reacts on hover, but **never with a plain lift-up** (`translateY` + shadow is DROPPED in `motion.md` — overused, generic). Replace the lift with something meaningful: a border-accent shift, a background wash, an accent element sliding in, a hidden detail revealing, an arrow easing in, the icon inside reacting. A bare hover-lift is the single most common slop tell and is **not allowed**.

**Links** — never just a color change. An underline that slides in, a marker that grows — a small constructed motion. Active state included.

**Inputs** — focus and hover both styled; label or border reacts; validation states animate in, never appear instantly.

**Tabs / toggles / segmented controls** — the active indicator **slides** between positions, never jumps. The moving indicator is mandatory.

**Accordions / expanders** — height and content animate open and closed; the icon changes with the state.

**Any state change at all** — loading→done, empty→filled, closed→open, theme A→B — **animates**. A state that snaps is a defect. If a thing can change, the change is shown moving.

## Replacements for the banned card-lift

When tempted to write `transform: translateY(-6px)` + shadow on a card hover, use instead one or more of:
- border color shifts toward the accent,
- a soft background wash fills the card,
- an accent bar or arrow slides in from an edge,
- a previously hidden line of detail expands into view,
- the card's icon scales/rotates slightly,
- inner content shifts to imply depth (parallax-lite).

The card must *respond* — it must not *jump*.

## Quality bar

Crisp, not sluggish (120–180ms for direct response; 200–400ms for larger reveals). `transform`/`opacity` only. `prefers-reduced-motion` collapses these to instant-but-defined states (the element still has its states; they just do not animate). Hover effects that depend on a pointer are disabled on touch but the element still has idle/active.

## Opt-in interaction sound (Phantom idea)

Subtle audio on interaction (hover, click, section-enter) is a memorable signature — but only
as **opt-in**. Ship a sound toggle that defaults **OFF**; when the user turns it on, play short
CC0 UI sounds on key interactions. Never autoplay, never on first load, respect a mute and
`prefers-reduced-motion`. Keep files tiny, preload on opt-in, source CC0 only (e.g. freesound.org
filtered to CC0). Bundle a small varied set (hover, tap, success, transition) so it isn't one
repeated blip. See `references/inspiration.md` (Phantom).

## Stateful icons without flicker

Paired icons (eye/eye-off, play/pause) must **morph or cross-fade**, never hard-swap or remount,
or they flicker mid-toggle. See `frontend-gotchas.md` #3.

## Status

The three-state requirement (idle/hover/active, all transitions animated), icon reaction on stateful controls, the card-lift ban with mandatory replacement, sliding active indicators, animated state changes: **MUSTHAVE-BASE**. Verified element-by-element at the QA gate — see `design-qa.md`.
