# Forms

A form is not "fields + a button" — it is a path the user must not stumble on. Every friction point lowers completion.

## Field layout

- **Label above the field** — never as a placeholder (the placeholder disappears on input, the user forgets what they were entering), never beside it.
- **One column by default.** Two columns only for short related pairs (city + zip).
- Field width hints at input length — a zip field is narrow, an email field is wide.
- Hints as small text under the field.
- A label is always present — for UX and for accessibility.

## Inline validation

- Validate **as the user goes**, not after submit — but **not on every keystroke from the first letter** (annoying). Validate after a pause or on blur; confirm correct values in green immediately.
- An error always carries a **concrete reason** ("needs the form name@mail.com"), never "invalid value".

## Multi-step wizard

A long form becomes 3–5 steps with a visible progress indicator. "Back" is mandatory and data is not lost on return. Group fields by meaning (one step = one topic). Step transitions are animated (slide), not jump-cuts.

## Error state

- Shown **next to the problem field**, not as a list at the top.
- Concrete reason; the field highlighted; a light shake to draw the eye.
- Focus moves automatically to the first errored field.
- Tone is helping, not accusing.

## Dangerous-action confirmation

- Irreversible actions are never one click.
- Levels: light (a normal "are you sure?" modal) for reversible; **strong** (type a confirmation word, or press-and-hold) for irreversible — account/data deletion.
- The final action button is inactive until the user has explicitly confirmed.
- Dangerous buttons get their own color (red), visually separated.
- **Where possible, prefer undo over confirmation** ("deleted — undo?") — safer and faster for the user.

## Cross-cutting

Everything appears and disappears smoothly — fields, errors, wizard steps, confirmations. No instant swaps.

## Status

- Label-above, one-column default, concrete-reason errors, error-next-to-field, dangerous-action protection, smooth appear/disappear: **MUSTHAVE-BASE**.
- Inline validation, multi-step wizard, undo-over-confirmation: **MUSTHAVE-DEFAULT** where the form calls for it.
