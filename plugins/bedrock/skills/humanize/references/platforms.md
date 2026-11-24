# Platforms

The deliverable is plain text the user copies as is. Never wrap a message in a
blockquote or callout: those paste as a bar or stray symbols. The one exception is in
SKILL.md, step 6: several messages are handed over one per bare code block, so each is
copied on its own.

## Slack (mrkdwn, not markdown)

- bold `*text*`, never `**text**`
- italic `_text_`, strike `~text~`
- inline code in backticks; a code block in triple backticks only for real code
- no headings; a `*bold line*` on its own line if a heading is truly needed
- links `<https://example.com|text>`, never `[text](url)`
- bullets `•` and a space; numbered lists `1.` work
- no `>` quotes in the deliverable

If the draft came out in standard markdown, run `scripts/to_slack.py` on it.

## Telegram

Plain text. Formatting symbols are not rendered when the user pastes into the app, so no
`*`, `_` or backticks around words. `•` for a list if one is really needed.

## Discord

Standard markdown works: `**bold**`, `*italic*`, `~~strike~~`, backticks, `-` bullets.
Still no blockquote around the whole message.

## Email

Plain paragraphs, no markup symbols. Emphasis comes from wording. Greeting and sign-off
only as short as the user's register allows.

## Plain

No markup at all. Lists only if the content is a list, with `•`.
