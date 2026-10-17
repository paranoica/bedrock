---
name: call
description: Debrief a call from its transcript — archive the raw text, extract decisions and debts with verbatim quotes and timecodes, check every quote. Use for "разбери созвон", "что решили на колле", "debrief the call".
---

# Call debrief

Omission and invention are the two failures of a meeting summary. Every item here carries
proof (D057).

## Triggers
- RU: «разбери созвон», «что решили на колле», «что говорил X про Y»
- EN: "debrief the call", "what did we decide", "what did X say about Y"

## 1. Archive the raw transcript
- Sources: Krisp, Google Meet notes, or local transcription (step 1b).
- `bedrock call add <file> --source <krisp|meet|whisper> --title "<title>" --date <YYYY-MM-DD>
  --participant <name> --language <en|ru>`. It prints the call id.
- The raw file is never edited: `bedrock call verify <id>` checks its checksum.
Done when: the id is printed and `verify` says `intact`.

### 1b. Local transcription
faster-whisper large-v3 (or large-v3-turbo for speed) with int8 on this machine's GPU,
through the heavy-run lock, in the background. Give it a hint vocabulary from the knowledge
base: names and terms of the project. Mark low-confidence spans `[?]`. Write the output with
`[hh:mm:ss]` line stamps, then archive it as above.
faster-whisper lives in its own environment: run it with
`~/.local/share/bedrock/whisper-venv/bin/python`. On this machine's GTX 1060 use
`compute_type="int8"` (no float16); when other programs hold the video memory, run it on the CPU.
Done when: the transcript is archived, or the missing package is reported.

## 2. Debrief
Copy `templates/kb/call.md` into the project's `calls/` folder in the knowledge base. The
first call of a project also creates the `calls.md` index (type `index`, parent `[[entry]]`)
and a row for it in the entry's canon table.
- Sections: Decided, We owe, They owe, New facts, plus contradictions with the base,
  questions for the next call, answers to open questions.
- Every item under Decided, We owe, They owe and New facts carries a verbatim quote and
  `(<call-id> @ hh:mm:ss)`.
- Mark "floated" versus "decided". A floated idea is never written as a decision.
- Label the whole transcript: item, chit-chat or unclear. Nothing is skipped silently.
Done when: `bedrock call quotes <id> <debrief.md>` prints `[]`, and every item section holds
items or the word "none". The check proves quotes, not coverage: the labelling does that.

## 3. A second pair of eyes
An `analyst` agent debriefs the same transcript from scratch, with a brief from
`templates/briefs/brief.md`, without seeing the first debrief. Show the owner the
differences, every "unclear" span and every `[?]` as one list.
Done when: the differences are resolved or listed for the owner.

## 4. Into the base and the backlog
- Decisions become decision notes (the `kb` skill). New facts update their notes.
- Our debts become backlog tasks. Tracker tickets only under the owner's grant.
- Questions for the next call go to the owner as a list.
Done when: `bedrock kb validate` is clean and the tasks are in the backlog.

## Finding what someone said
`bedrock call search "<phrase>"` searches every archived call and returns the call id, the
time and the line. Answer with the quotes and their times, never a paraphrase alone.
