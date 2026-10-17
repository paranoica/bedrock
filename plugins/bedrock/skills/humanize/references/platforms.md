# Platform formatting

How to format the finished text for each target. Default is Slack. The one rule that spans
every platform: **the deliverable is plain text**. Never wrap it in a markdown blockquote,
callout, or code fence, those render as a vertical bar or monospace and copy stray characters
into the destination. That junk is the whole reason this skill exists.

## Slack (default) — use mrkdwn, not standard markdown

Slack's syntax is called mrkdwn and it differs from normal markdown in ways that break silently
when you paste standard markdown in.

- **Bold**: single asterisks, `*bold*`. NOT `**bold**`. Double asterisks show up as literal
  characters, this is the classic broken-paste symptom.
- **Italic**: underscores, `_italic_`.
- **Strikethrough**: single tilde, `~strike~`. NOT `~~strike~~`.
- **Inline code**: backticks, `` `code` ``. Code block: triple backticks (no language hint,
  Slack ignores it).
- **Headings**: none exist. Use a `*bold line*` on its own line as a faux heading.
- **Links**: `<https://example.com|link text>`, NOT `[text](url)`.
- **Bullets**: use the `•` character followed by a space. Do NOT use `*` for bullets, it
  collides with bold. A leading `-` mostly works but `•` is safest.
- **Numbered lists**: `1.` `2.` etc, that part matches normal markdown.
- **Line breaks**: real newlines. Keep them, Slack respects them.
- **No `>` blockquote in the deliverable.** That's the vertical-bar block, skip it.

So a de-slopped Slack update looks like plain lines with `*single-asterisk*` emphasis and `•`
bullets, nothing else.

## Telegram

Keep it simple. Plain prose, `•` bullets if needed, minimal or no inline formatting. Telegram's
markdown modes are finicky and unescaped characters can fail to send, so when in doubt output
clean plain text with no markdown symbols.

## Discord

Standard markdown works here: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, `-` bullets.
This is the one place double-asterisk bold is correct. Still no forced blockquotes in the
deliverable.

## Email

Plain prose in real paragraphs. No markdown symbols visible at all (no `*`, `#`, `-` as
markup). If you need emphasis, rely on wording, not symbols. Short paragraphs, clear line
breaks.

## Plain

Strip every markdown symbol. Just clean text. Use `•` for bullets only if a list is genuinely
needed, otherwise prose.

## Sanitizer

If you drafted in normal markdown out of habit, run the draft through `scripts/to_slack.py`
before handing it over. It converts `**bold**` to `*bold*`, headings to bold lines,
`[text](url)` to `<url|text>`, `~~` to `~`, leading `-`/`*` bullets to `•`, and unwraps `>`
blockquotes. It's a safety net, not a substitute for writing mrkdwn directly.
