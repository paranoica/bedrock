---
name: humanize
description: Make a text sound like the owner wrote it, in Russian or English, copy-ready for Slack; replies to pasted threads. Use for "очеловечь", "ответь ему", "humanize", "draft a reply".
---

# Humanize

Turn AI-flavored or rough text into something a specific real person would actually
send. Two jobs, always in this order: strip the AI tells (slop), then apply the right
human voice and format it clean and copy-ready for the platform.

## Always start here

1. Read the owner's profile, `~/.config/bedrock/voice.md`. It holds their voice (two
   different registers, one per language) and all settings, and it overrides every
   default in this file. It lives outside the plugin, so the public repository never
   holds it. Missing or still the blank template (`config/profile.template.md`): run
   setup first (`setup/questionnaire.md`).
2. Open `skill-map.json` and load only the reference files this request needs.
3. Decide the output language (RU or EN) and the mode (reply / document / rewrite).

## Modes

**reply** — the user pasted a message or thread (text or screenshot) and wants an
answer. Match the thread: tone, register, spelling, punctuation, formality. Keep it
as short as the content allows. Load `references/style-matching.md` and
`references/anti-hallucination.md`. Never invent facts that aren't in the thread.

**document** — a doc, spec, post, or longer piece. For the client, the owner's voice.
For anyone else, a neutral, clean voice, unless told otherwise. De-slop fully. Longer is allowed
here, but stay tight.

**rewrite** — the default. The user handed you text to clean up. Keep the meaning,
strip the slop, fix the formatting, output something ready to paste.

## The two passes

Run both, in order, every time.

**Pass 1, de-slop.** Load `references/antislop-core.md` plus the language file
(`antislop-ru.md` or `antislop-en.md`). Hard mode is on: the full ban list applies and
dashes go to zero (the RU file explains how to restructure so the text still reads
right).

**Pass 2, voice + format.** Apply the voice from the profile, or match the thread in
reply mode. Then format for the platform via `references/platforms.md`. Default
platform is Slack.

## Output rules, this is the whole point

- Output ONLY the finished text. No preamble, no "here is your text", no summary of
  what you changed, no trailing offer to help. The user copies your output verbatim,
  so anything extra becomes junk they have to delete.
- Plain text. Never wrap the deliverable in a markdown blockquote (`>`), a callout, or
  a code fence. Those render as a vertical bar or monospace and drag stray characters
  into Slack when the user copies them. This is the exact problem the skill exists to
  avoid.
- For Slack, write mrkdwn, not standard markdown: single-asterisk `*bold*`, `•`
  bullets, no `#` headings. Full rules in `references/platforms.md`.
- To be safe, you can pass your draft through `scripts/to_slack.py` to catch stray
  `**`, `#`, `>`, and markdown links before handing it over.
- Before handing it over, always run the mechanical check on the draft:
  `printf '%s' "<draft>" | bedrock text check - --slack` (drop `--slack` for plain text).
  It must print `[]`. It catches dashes, stock filler phrases and markdown Slack shows raw.
  Fix what it finds and run it again.
- It is a draft. Claude never sends it (D044). Only on the owner's request does it go into
  his own Slack drafts, after a test draft to himself showed no "sent with Claude" label.

## Commands

- `/bedrock:humanize [text]` — clean and format [text] using the profile, mode auto-detected.
- `/bedrock:humanize [text]` with a pasted thread — reply mode.
- `/bedrock:humanize slack [text]` — force Slack mrkdwn output.
- `/bedrock:humanize plain [text]` — force plain text with no platform formatting.
- `/bedrock:humanize doc [text]` — force document mode.
- `/bedrock:humanize setup` — run the questionnaire and produce the profile's text.

## When something is missing

- No profile, or it's still the template → run setup first.
- Reply needs a fact you don't have → leave a `[confirm X]` gap, do not guess. See
  `references/anti-hallucination.md`.
- Platform unclear → ask once, or fall back to plain text.
