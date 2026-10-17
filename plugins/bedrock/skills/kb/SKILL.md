---
name: kb
description: Write and keep the project knowledge base — decisions, failures, module notes, runbooks, calls; validate, fix drift, find gaps. Use for "запиши решение", "обнови заметку", "record a decision", "kb".
---

# The knowledge base

One store for all projects: `~/projects-memory-bank/<project>/`, a local git repository
(D023). Notes are English, the owner hears about them in Russian (D025).

## Triggers
- RU: «запиши решение», «зафиксируй», «обнови заметку», «что в базе устарело»
- EN: "record a decision", "write it down", "update the note", "what is stale"

## What goes in
Only what the code cannot tell: decisions and their why, failures, call outcomes, domain
pitfalls, people, external constraints (D024). A note that restates code is not written.
Day logs, raw transcripts and edit history stay out.
A decision note is written only when the choice was contested, the obvious option was wrong
for a reason that is not obvious, or a later session could plausibly undo it.
Project facts never go to Claude's memory, even on «запомни» (D027). That memory holds facts
about the owner only.

## 0. A project without a folder
`bedrock kb init --code ACME` creates the minimal folder: entry, summary, status and the
indexes. The code is the prefix of every decision and failure code (`ACME-D12`).
Done when: `bedrock kb validate` prints `[]`.

## 1. Write a note
1. Pick the template from `templates/kb/`: decision, failure, module, runbook, call, faq,
   status, handoff.
2. One topic per note. Split it when it grows past the validator's limit.
3. Every fact carries its source (file:line, commit, call time, a message link) and an
   evidence mark: verified at the source, secondary, hypothesis, or needs a third party.
4. Link it from its index (`decisions.md`, `architecture.md`, …). An unlinked note is an
   orphan.
5. A module note sets `covers:` (the paths), optional `anchors:` (symbols) and
   `verified_at:` (the commit it was checked at).
Done when: `bedrock kb validate` is clean.

## 2. Decisions are never edited
A changed decision is a new note. The old one gets `status: superseded` and a link to its
successor. A link that treats a superseded decision as current is flagged by the validator.
Done when: the new note validates and the old one says `status: superseded`.

## 3. Keep it fresh (D026)
The hooks do the detection. The session does the fix.
- Session start lists stale module notes (`bedrock kb drift`) and modules without a note
  (`bedrock kb uncovered`, when the project sets `kb.roots`).
- Stop blocks once when code under a module note changed and the note did not. Fix it in
  one of two ways:
  - update the note's Boundaries, Rules or Pitfalls;
  - add one line: "verified, nothing to change, because …".
  Then set `verified_at` to the new commit. A new `verified_at` alone is never a
  verification. The hook compares the note's content, not its stamp.
- Every two weeks, with the architecture review: delete dead notes, re-check orphans and
  notes long untouched.
Done when: `bedrock kb drift` lists nothing for the touched modules.

## 4. Commit the store
`git -C ~/projects-memory-bank add <project> && git -C ~/projects-memory-bank commit -m
"docs(<project>): <what>"`. Stop treats uncommitted notes as an unclosed phase. The store is
never pushed. Only the encrypted backup leaves the machine (`bedrock backup`, D030).
Done when: `git -C ~/projects-memory-bank status --short` prints nothing.

## Finding things
- `bedrock kb backlinks <note>`: what links to a note.
- `grep -rl <word> ~/projects-memory-bank/<project>`: no vector search (D023).
