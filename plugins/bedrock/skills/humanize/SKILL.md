---
name: humanize
description: Make a text sound like the owner wrote it — strip AI tells, match the thread, format for Slack or plain text, copy-ready. Use for "очеловечь", "ответь в треде", "humanize", "draft a reply".
---

# Texts in the owner's voice

The output is pasted as is. Anything around it is junk the owner has to delete.

## Triggers
- RU: «очеловечь», «ответь ему», «напиши в слак»
- EN: "humanize this", "draft a reply", "write it for Slack"

## 0. The voice
The owner's voice lives in `~/.config/bedrock/voice.md`: how he writes in Russian and in
English, words he uses and avoids, how formal he is with whom. It is his file, outside any
repository. Missing: ask five questions (below), write it, then continue.
1. How do you greet and sign off with the client, with the team?
2. Short sentences or long? Emoji, yes or no?
3. Words you never use?
4. «Вы» or «ты» with whom?
5. Paste two messages you wrote that you like.
Done when: the file exists.

## 1. Pick the mode
- **reply:** a pasted message or thread. Match its language, register and length. Answer
  only what was asked. A fact the thread does not hold is a `[уточнить: …]` gap, never a guess.
- **document:** a longer piece. A neutral clean voice, not the personal one.
- **rewrite:** the default. Keep the meaning, change the form.
Done when: the mode is chosen.

## 2. Strip the tells
- No dashes (— or –). Split the sentence, or use a comma or a colon.
- No filler: "стоит отметить", "надеюсь, это поможет", "I hope this helps", "feel free to".
- No summary of what was just said, no offer to help further, no praise of the question.
- Concrete over abstract: the number, the name of the thing, the date.
- Lists only when the content is a list.
Done when: `bedrock text check <file>` prints `[]` (add `--slack` for Slack).

## 3. Format for where it goes
- Slack (the default): `*bold*` with single asterisks, `•` bullets, bare links, no `#`
  headings, no `>` quotes, no tables.
- Plain text: no markup at all.
Done when: `bedrock text check --slack` is clean for Slack text.

## 4. Hand it over
Output only the finished text: no preamble, no "вот текст", no blockquote or code fence around
it. It is a draft. Claude never sends it (D044).
