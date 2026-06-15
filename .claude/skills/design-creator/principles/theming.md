# Theming

## Two themes — strong default, not an absolute

Two themes (light and dark), dark usually the default, is the **strong default** — most products benefit and users rarely regret asking. But it is not an unconditional MUSTHAVE-BASE: some designs are mono-theme by art direction (a cinematic dark-only brand, a print-like editorial site), and forcing a second theme there dilutes the concept and roughly multiplies Stage-1 mockup cost.

So: the engine ships two themes by default, but when the hook or family clearly wants a single theme, it **says so and asks** ("dark-only reads stronger for this concept — make a second theme anyway?"). The decision is the user's; the default stands if they don't object. This is an override of the same shape as `mode` — a default with a stated, user-confirmed exception, not a silent choice.

When the project is mono-theme, the dark/light *depth model* still differs (`depth.md`): on dark, elevation is carried by light and a top hairline, not by shadow — dark mode is its own design, not an inversion.

## The transition

The two themes change one into the other with a **smooth animated transition** — not an instant swap. Two acceptable forms:
- a circular reveal (comic-panel style) — this is the View Transitions API,
- or a smooth color cross-fade.

A theme toggle control is always present.

## Anti-FOUC

Prevent a flash of the wrong theme: an inline script in `<head>` that sets the theme before paint; a `color-scheme` meta. The concrete implementation is read from / aligned with the project's `CLAUDE.md` if it already solves theming.

## Corner-shape: squircle (progressive enhancement)

Where corners are a brand surface, `corner-shape: squircle` with a `border-radius` gives the fuller, softer superellipse corner ("iOS" feel) instead of a circular arc. Chromium 139+; everywhere else it gracefully falls back to the plain radius, so it's safe to ship as an enhancement. Apply it as a token (one place), not per-component.

## Status

- Two themes, theme toggle, smooth animated transition, anti-FOUC: **MUSTHAVE-BASE**.
- The transition *form* (circular reveal vs color cross-fade): **SITUATIONAL** — chosen with the user.
