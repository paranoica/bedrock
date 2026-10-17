# Screen States

Screen states are full screens, not placeholders. Each answers "what happened" and "what to do next" — none leaves the user in a dead end. The skill defines the **skeleton** (what is on screen and why); the visual execution is built to the project's design system.

## Empty

A bare empty screen reads as "broken". A correct empty state: an icon / mini-illustration, a short heading of what is happening, one line of explanation, and — crucially — an **action button** that leads out of the emptiness. The icon is static — movement without meaning is wrong. Different causes get different copy: "nothing yet" (new user) ≠ "nothing found" (filter) ≠ "all done" (tasks closed).

## 404

**Always custom**, in the site's styling and theme — a default browser 404 reads as "unfinished". A custom 404 can be bright, playful, themed, even carry a 3D object or animation. But under the play: always a way back (home + one or two useful links), never a dead end.

## Error

What happened in plain language, no codes or stack traces (those go to error tracking, not the user). Where possible, what to do. Always a "Retry" button — most errors are transient. A local error shows in its block, not instead of the whole screen.

## 500

The server is at fault, not the user — say so explicitly ("it's not you, it's us"). Tone more restrained than 404 (the user wanted to do something and could not). A refresh button + a path to support. Honesty ("we're already fixing it") beats vague wording.

## Success

Not just closing the form — mark the moment: a calm success indicator (it need not be a green check-circle — the indicator form is the project's call, as long as it reads as "done"), a concrete confirmation ("Tuesday 18:00", not "Success!!!"), and a next step so the user is not stranded. Dose it: a routine action gets a light toast; a major one (payment, registration) gets a full screen.

## Cross-cutting

The skill gives the structure (what must be on screen and why), not the exact visual — visual is per project. All states appear/disappear smoothly.

## Status

- Every state present and never a dead end, "what happened + what next", custom 404, smooth appear/disappear: **MUSTHAVE-BASE**.
