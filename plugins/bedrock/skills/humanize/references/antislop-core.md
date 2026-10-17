# Anti-slop, core (language-independent)

These patterns read as AI in any language. Fix them in pass 1, before you touch voice or
formatting. The guiding idea: one instance of any pattern can be fine, the tell is
**density**, several of these stacked in one short piece. Cut ruthlessly, because the owner
runs anti-slop on HARD.

## Rhythm and structure

- **Vary sentence length.** AI writes at a metronome pace, every sentence about the same
  length. Mix short and long. Let some run on a little, cut others to three words.
- **Kill the rule of three.** "fast, clean, and reliable", "we built, we shipped, we
  learned". Triples everywhere are a tell. Use one or two, or four, or none.
- **Drop the rigid template.** Intro, three tidy body chunks, a wrap-up. Real messages
  don't announce their structure. Start in the middle if that's where the point is.
- **No manufactured fragments for drama.** Standalone one-word "sentences." For emphasis.
  Like this. That cadence is an AI habit, not how people actually write.

## False weight

- **No inflated stakes.** Not every update is pivotal, transformative, or a turning point.
  A deploy note is a deploy note. Say what happened.
- **No moralizing wrap-up.** Don't end on a little lesson about the bigger picture. Stop
  when the information stops.
- **No fake insight reveal.** "But that's not the real story. The real story is..." /
  "Here's the thing:". Just state the thing.
- **No "obvious / clearly / simply"** to assert a point you haven't shown. If it were
  obvious you wouldn't need to say so.

## Negative parallelism (the single most recognizable tell)

Ban the "not X, but Y" / "it's not X, it's Y" reframe and all its variants: the causal
"not because X, but because Y", the countdown "not a bug. not a feature. a flaw.", the
cross-sentence "the question isn't X, the question is Y". One of these poisons a whole
message. Say the positive thing directly.

## Vague authority and hedging

- **Name the source or drop it.** "experts say", "studies show", "it's widely reported"
  with no name is filler. Either cite the actual thing or make the claim in your own voice.
- **No invented specifics.** Never fabricate a statistic, quote, date, or example to sound
  grounded. A made-up "73% of teams" is worse than no number.

## Signposting and filler transitions

Cut phrases that announce a move without making one: "it's worth noting", "importantly",
"that said", "when it comes to", "in terms of", "at the end of the day", "needless to say".
And cut the pedagogical voice: "let's dive in", "let's unpack this", "let's explore". Write
to a peer who doesn't need hand-holding.

## Punctuation

- **Dashes to zero** (owner setting, hard). Em-dash and en-dash out. Language files say how
  to restructure so the sentence still reads right.
- **No exclamation spam.** At most one, and only if the register genuinely calls for it.
- **No trailing "..." for suspense.** Ellipsis only for a real trailing-off or an omission.

## Formatting

- **No bolded lead-in on every bullet.** "**Fast:** it runs quickly. **Cheap:** it costs
  less." Nobody writes lists by hand this way. If you bullet at all, keep the items plain.
- **No emoji** unless the profile allows it for that register.
- **No markdown that leaks as literal symbols** in the target surface. See
  `platforms.md`.

## The test

Before you hand it over, reread it and ask: would a specific real person send this exact
message? If any line reads like it came from a generic assistant, rewrite that line. Prefer
concrete and specific over smooth and general. Boring-but-real beats polished-but-hollow.
