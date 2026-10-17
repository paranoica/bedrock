# Setup questionnaire (/humanize:setup)

The goal is to converge on the owner's ideal voice by showing concrete examples and letting
them pick and tweak, not by asking abstract questions. Calibrate, don't interrogate. A person
can't reliably describe their own style in the abstract, but they can instantly point at the
sample that sounds like them.

Run in this order. Use the host's tappable/popup UI for the picks (buttons beat typing).
Between steps, keep it short. At the end, put everything into the profile's text, flip
`Status: template` to `Status: configured`, and give the text to the owner to save (step 8).

## 1. Languages

Ask which languages they write in and which is primary.
Options: RU / EN / both equally / other (specify).
Each language gets its own voice block later. Never merge them.

## 2. Platform

Where the output usually lands, and the default.
Options: Slack / Telegram / Discord / email / plain text / ask each time.
This decides the formatting rules in `references/platforms.md`.

## 3. Style calibration (the core step)

For each language, show the SAME short message written a few ways and ask which is closest.
This anchors the voice on something concrete. Present the archetypes below (adapt the content
to something from the owner's world if you know it).

### EN archetypes — content: "the deploy is fixed and live on staging and prod"
(no apostrophes, no trailing periods, commas dropped where the line still reads)

- A. Terse-casual: `deploy is fixed live on staging + prod`
- B. Warm + dry casual (the owner's target): `Yeah deploy is fixed and live on staging and prod`
- C. Neutral-plain: `The deploy is fixed and live on staging and prod`
- D. Punchy-direct: `Deploy fixed. Live on staging and prod`

### RU archetypes — content: "починил деплой, уже на проде, дубли релизов ушли"

- A. Строчный очередями: `починил деплой` / `на проде уже` / `дубли релизов ушли` (три строки)
- B. Разговорный-аккуратный: `деплой починил, уже на проде. дубли релизов больше не плодятся`
- C. Нейтральный: `Деплой исправлен, изменения на проде.`
- D. Сухой-технический: `фикс задеплоен. прод. дубли тегов пофикшены`

Ask the owner to pick the closest per language (buttons A/B/C/D). The pick sets the starting
register. Then ask one nudge question: shorter or longer? warmer or drier? more slang or less?
more punctuation or less?

## 4. Calibration loop (converge on "that's me")

Take the picked archetype plus the nudge, and generate ONE fresh sample on a topic the owner
gives (or a plausible one from their context). Show it. Ask: closer, or adjust? Let them say
"warmer", "shorter", "more like how I actually type". Regenerate. One or two rounds is usually
enough. Stop when they say it sounds like them.

This loop is what makes the profile fit. Don't skip it for the primary language.

## 5. Real samples (best signal, optional)

Ask for 3-5 real messages per language, pasted as-is with real typos and punctuation. If given,
distill the fingerprint from these and let them OVERRIDE the archetype pick, real samples always
win over calibration. If skipped, the calibrated archetype is enough to start, note in the
profile that samples can be added later to sharpen it.

## 6. Behaviour toggles

Quick buttons, each maps to one line in the profile Settings block:

1. Anti-slop hardness: hard (full ban + zero dashes) / contextual / soft.
2. Dashes per language: zero (restructure) / keep grammatical. (RU note: a dash is normal RU
   grammar, so "zero" means reorder or use comma/colon, hyphen only as last resort.)
3. Profanity: never / match interlocutor / ok in casual / free.
4. Emoji: never / rare and fitting / match interlocutor.
5. Output format: plain text / block with copy button / depends on platform.
6. Length: always concise / match thread / clean only, keep as-is.
7. Replies: one / two variants / depends on importance.
8. Base register when writing first, per language: informal / neutral / formal.
9. Documents voice: owner's personal voice / neutral clean / ask each time.

## 7. Free-text

- Stop-list: words or phrases to ban forever, on top of the anti-slop lists.
- Context: who they message and about what, so reply mode doesn't fabricate facts.

## 8. Write the profile and confirm back

Map every answer into the profile's text (the shape of `config/profile.template.md`):
- calibrated style + samples → the two voice register blocks
- toggles 1-9 → Settings
- stop-list → Stop-list
- context → Context

Flip the status line to `configured`. Then read the distilled voice back to the owner in a few
bullets and let them correct it. Give the owner the final text to save as
`~/.config/bedrock/voice.md`: bedrock's guard keeps Claude from writing that folder. A wrong voice profile is worse than a thin one.

## Re-running setup

On a rerun, load the current profile, show what's set, and change only the fields the owner
wants. Don't wipe good answers to re-ask everything. Offer the calibration loop again if they
say the voice feels off.
