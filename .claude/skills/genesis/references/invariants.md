# Invariants — re-read at each phase boundary, before writing any spec doc, and at the spec-analyze gate

The compact, non-negotiable core. Short by design so reinjection is cheap. Do not assume you
"already read it" earlier in a long session — re-read.

## The generator's prime directive
0. **Write what passes your own gate, first try.** Everything genesis produces must pass
   `spec-analyze` without rework. If the generator routinely emits what its own gate rejects, the
   generator and the gate have diverged — fix the generator, never loosen the gate.

## Truth & grounding
1. **Never invent a missing decision.** Unknown is first-class: record `TODO(decision: …)` in
   `open-questions.md`. A guess presented as settled is the worst failure mode.
2. **Spec is the source of truth.** `docs/` (decisions → architecture → glossary → open-questions)
   wins. The backlog, the map, and `project-context/` are derived or historical — never authoritative.
   On any conflict with `project-context/`, the spec wins (it is later and resolved).
3. **Don't pass a guess off as grounded.** When a choice has no input behind it, flag it.
   In **adopt** mode: observed facts → `architecture.md` **with file:line citations**; reverse-inferred
   rationale → `open-questions.md` as `inferred/unconfirmed`, **never** asserted in `decisions.md`.

## Anchoring & re-derivability (see `anchor-contract.md` — the one source)
4. **Every atomic spec unit carries a stable anchor.** Decisions, glossary terms, and architecture
   invariants are anchored. Partial annotation, dangling refs, duplicate ids = CRITICAL.
5. **One normalizer, one hash.** Hashes are computed only by `scripts/anchors.py` (via `backlog.py
   stamp`) — never hand-written, never a second implementation. Generator and gate share it so a
   fresh backlog has zero phantom drift.
6. **Every domain noun has a term-anchor.** A term used in a decision or a task `acceptance` must be
   defined in `glossary.md` with a `term:` anchor and listed in the referencing unit's `refs:` (so
   transitivity reaches it). Close this while writing — don't leave it for the gate.
7. **Re-derive, don't freeze.** On spec change: content drift → `needs-review` (soft); structural
   change → `stale`/re-split; preserve `done` (drifted `done` → `needs-review`, never silently un-done).

## Backlog discipline
8. **State changes only via `backlog.py`.** `genesis.tasks.json` is the single source of task state;
   `PLAN.md` is a GENERATED render — never hand-edit either.
9. **Decomposition cap = verifiability.** Two subtasks may not be split unless each gets a
   distinguishable `verify` handle + `acceptance`. (`effort:S|M|L` is advisory, never gates depth.)
10. **Each task is self-contained.** `acceptance` (EARS array), `verify {kind,handle}`, `files`,
    and `spec_refs` (the single task→spec link). A task whose `spec_refs` includes an open
    `TODO(decision:)` is flagged by the gate as resting on an unresolved decision — not executable yet.

## Governance & interview
11. **Never overwrite `AGENTS.md`'s universal section, a wrapper (`CLAUDE.md`, …), or any user work.**
    Project rules go inline in `AGENTS.md`'s Project-rules section; read-and-extend; surface conflicts.
12. **Interview depth scales to complexity** (branch-activation gates, not a score). One open
    question at a time; group only discrete forks **within** a branch, never across branches.
13. **Hand design-creator structured constraints only** — domain, audience, surfaces/page list,
    in/out scope, tone, brand assets. **Never a hook or a narrative** (it collapses dc's diversity).
14. **The spec-analyze gate is blocking and receipt-bound.** Never declare the spec/backlog ready
    on a skipped gate.
