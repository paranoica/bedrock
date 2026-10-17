# Humanize — Profile (TEMPLATE)

This is the blank template. The skill treats a profile in this state as "not configured"
and will run `/humanize:setup` first. Setup fills every field below from the
questionnaire, then flips the status line to `configured`.

Status: template.

## Owner voice — two registers, never merge them

Fill one block per language you write in. Capture how you actually write, not how you
"should" write. Paste 3-5 real messages per language during setup and let the skill distill
the signals into the bullets here.

### <language A> register (<context, e.g. internal / with teammates>)

- <capitalization: lowercase? sentence case?>
- <length and rhythm: short bursts? full paragraphs?>
- <recurring words, slang, fillers>
- <punctuation habits>
- <how you explain technical things>
- <emoji: yes / no / which>

### <language B> register (<context, e.g. client-facing>)

- <same set of signals for the second language>

## Settings

- **languages**: <e.g. RU + EN, auto-detect, separate configs>
- **anti-slop**: <hard = full ban / contextual / soft>
  - <per-language dash rule>
- **profanity**: <never / match interlocutor / ok in casual / free>
- **emoji**: <never / rare / match interlocutor>
- **output**: <plain text / block with copy button / depends on platform>
- **length**: <always concise / match thread / clean only, keep as-is>
- **default platform**: <slack / telegram / plain / ask each time>
- **reply mode**: <one reply / two variants / depends>
- **base register when writing first**: <informal / neutral / formal, per language>
- **documents mode**: <owner voice / neutral clean / ask>

## Stop-list (ban permanently, on top of the general anti-slop lists)

_(add words or phrases here, one per line)_

## Context (so replies don't fabricate)

<who you talk to, about what, so reply mode doesn't invent facts>
