# Mode: adopt

An existing repo with code but no canon / spec / map. genesis bootstraps the spec + canon + first
map **without reviewing the code** (auditing is code-review's job).

## The honesty rule (this mode's whole point — the most hallucination-prone path)

You can observe **what** the code is; you cannot know **why** it was decided. So:
- **Observed facts → `architecture.md`, WITH `file:line` citations.** "The API exposes `POST /login`
  (`api/auth.py:88`)" is a fact you read.
- **Reverse-inferred rationale → `open-questions.md` as `inferred/unconfirmed`** — never asserted in
  `decisions.md`. Write: `TODO(decision: confirm <X> — inferred from <file:line>; intentional?)`.
- A decision graduates to `decisions.md` **only after the human confirms it**. `spec-verifier` flags
  any `decisions.md` entry whose rationale has no confirmed provenance (invented-decision).

## Steps
1. Preflight, then build the map: `tools/project-map/build.py <root>` to see structure, routes,
   data-model, queues.
2. Read the map's **slices as LEADS** — open each `file:line` and confirm. Never assert a slice as fact.
3. Draft `architecture.md` (observed, cited) + `glossary.md` (terms actually in use) +
   `open-questions.md` (inferred rationale, pending confirmation).
4. Short interview: confirm inferred decisions, fill scope/MVP and anything the code can't reveal.
5. **Read-and-extend** any existing `CLAUDE.md`/`AGENTS.md` (never overwrite); fill `AGENTS.md`'s
   "Project rules" section inline.
6. Derive a backlog for the **work the user wants next** — not a rewrite of what already exists.
7. `backlog.py stamp` · `calibration.py snapshot` · run the gate.
