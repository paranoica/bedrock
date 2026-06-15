# Interview taxonomy + generation chain

How genesis interviews the user (in the user's language) and turns answers into anchored spec docs
and self-contained tasks. The runtime interview is conversational; this file is the scaffold, not a
script read aloud. Anchors/normalizer/hash live in `anchor-contract.md` (the one source).

## 1. Complexity triage = branch-activation gates (NOT a score)

Depth is not a 1–10 guess (we rejected that for tasks; we reject it here too). It is the **sum of
activated branches**. Each gate is a cheap yes/no read of the brief; a "no" skips the whole branch.

| Gate | Fires when the product… | Activates branch → feeds |
|------|--------------------------|--------------------------|
| *(always)* | exists | **purpose** → `decisions`, `glossary` |
| scope | — (always asked once) | **scope** (in-MVP / explicitly-out) → `decisions` |
| project-type | always, early | **project-type** (web-app / service-API / CLI / library / worker / …) → drives the design handoff AND the CI prototype (`ci-emit.md`) |
| data-model? | persists domain entities | **entities** (entities, relations, status enums) → `architecture` data-model + `term:*` |
| auth? | has accounts/identity | **auth** (identity model, roles, permissions) → `decision:auth-*` |
| money? | moves money | **money** (who pays whom, when; refunds/payouts) → `decision:money-*` |
| integrations? | calls external services | **integrations** (which, contract) → `decision` + `open-questions` |
| non-functional? | has scale/SLA/compliance needs | **nfr** (perf, SLA, regulatory) → `architecture` |
| surfaces? | has client surfaces | **surfaces** — list them. **Visual web surfaces** (pages/screens) → **design-brief** for design-creator. **Non-visual** (CLI commands, API endpoints, worker jobs) → recorded as scope only, **NO design handoff** (design-creator is web-visual-only). |
| agents (1 grouped Q) | always, late | **agents** — which coding agents the team uses (multiselect) → per-agent **wrappers** emitted in Phase 4 |
| *(always last)* | — | **open-decisions** sweep → `open-questions` |

- **Trivial brief** (1 surface, no money, no data model) → ~2 branches fire → 2–3 questions, then
  step aside (do the thing, briefly). **Multi-surface** → most branches fire → dig to the bottom.
- Branches that don't apply are skipped **entirely** — never asked "for completeness".
- **project-type gates the design handoff.** Only a project with a real **visual web surface**
  (web-app / dashboard) yields a `design-brief` → design-creator. `cli` / `library` / `service-API` /
  `worker` → **no design-brief** (design-creator is web-visual-only). project-type also selects the CI
  prototype (`references/ci-emit.md`).
- **The agents gate is ONE grouped multiselect** (Claude / Cursor / Codex / Aider / Continue /
  Antigravity) in the tooling branch — never mixed with product branches. **Golden-default
  = Claude + the shared `AGENTS.md`** (covers most agents natively). If the user doesn't answer, don't
  interrogate about six tools — ship the two base wrappers and move on. Drives Phase 4 wrapper emission.

## 2. Cadence — the one-question rule and its boundary

- **Open prose questions: strictly one at a time.** Entities, "the core job", money flow shape —
  these are elicited one per turn. A wall of open questions was the #1 elicitation failure.
- **Discrete forks may be grouped — within a single branch only.** A multiple-choice
  `AskUserQuestion` may bundle the discrete toggles of *one* branch (e.g. auth: provider options +
  role set together; or scope: which surfaces are in-MVP). **Never group across branches** (auth +
  money in one prompt is forbidden — that recreates the wall).
- **Questions may surface in context**, when a branch is reached — not dumped up front.
- **Golden default:** if the user says "just do what's best, don't grind me", proceed on sensible
  defaults but still extract the minimum that genesis cannot invent (scope, the core entities,
  money custody if money is involved). Never work on zero input.
- **Never invent.** Any answer the user can't give → `TODO(decision: …)` in `open-questions.md`,
  with options/leaning if any. Move on; do not stall the whole interview on one unknown.

## 3. The generation chain (answer → anchored unit → task)

1. **A settled answer becomes an anchored atomic unit:**
   - a decision → `decisions.md` with `<!-- @anchor decision:<slug> refs:term:… -->` (ADR shape);
   - a domain entity/concept → a `term:` anchor in `glossary.md` **and** (if persisted) an entry in
     the `architecture.md` data-model;
   - a structural invariant → an `arch:` anchor (cross-cutting).
2. **An unknown becomes a `decision:` anchor in `open-questions.md`** (same `decision:` namespace, so
   when it is later resolved it graduates to `decisions.md` keeping the same slug — tasks that keyed
   `spec_refs` on it stay valid across the move).
3. **Tasks derive from the spec.** Each task: `acceptance` (EARS array), `verify {kind,handle}`,
   `files`, and `spec_refs` (the **single** task→spec link — its keys *are* the trace). Hashes are
   stamped by `backlog.py` via the shared `anchors.py`, never by hand.
4. **Open decisions stay wired — to their real dependents only.** A task that depends on an open
   `TODO(decision:)` lists that id in its `spec_refs`. `spec-analyze` then flags the task as resting
   on an unresolved decision — it cannot be declared execution-ready. The unknown physically blocks
   the dependent work instead of floating as a note. **(Model pattern — keep it.)**
   **Do NOT `refs:` an open decision from a *settled* decision** — every task tracing the settled
   decision would then inherit it through the closure and be falsely blocked (over-firing). Wire the
   open decision straight into the `spec_refs` of the tasks that actually need it (e.g. only the
   remote-driver task, not the local-write task).

## 4. Term-anchor discipline (refinement: close the gap at write-time)

Every domain noun that appears in a `decision` body or a task `acceptance` MUST have a `term:`
anchor in `glossary.md`, and the using unit MUST list it in `refs:`. The generator closes this as it
writes — if it names `escrow`, `claimable`, `commission` in an acceptance, it adds those glossary
terms in the same pass and references them.

**Honest enforcement boundary** (so the gate doesn't itself lie about what it can prove):
- **Mechanically CRITICAL** (`analyze_spec.py` can prove these): a `refs:`/`spec_refs` id with no
  matching anchor (**dangling**); a must-anchor file with mixed anchored/unanchored units
  (**partial annotation**); a duplicate id.
- **Heuristic WARN, not auto-CRITICAL**: a capitalized/repeated domain-looking noun in a decision or
  acceptance that has no glossary term. analyze surfaces it for the generator to either anchor or
  confirm-not-a-term — it does **not** hard-fail, because it cannot reliably know which words are
  domain nouns. Closing it is generator discipline; the WARN is the assist.

## 5. Worked shape (reference)

Brief "storage-unit rental marketplace" fires data-model+auth+money+integrations+surfaces → deep.
Output: `decision:auth-model` (D-001), `decision:money-custody` (D-002, `refs:term:booking,term:payout,term:escrow,term:commission`), `decision:payment-provider` as an **open** TODO; tasks trace via
`spec_refs`; the escrow/payout task lists `decision:payment-provider` in `spec_refs` → gate flags it
as blocked-on-unresolved-decision. From the surfaces answer, a `design-brief` (surfaces, audience,
tone, in/out) is assembled for design-creator — **no hook, no narrative**.

## 6. After the interview

State the spec narrative back to the user in plain words (decisions + open questions) → **STOP, the
spec-confirmation gate** → on confirm, generate `docs/` + backlog + canon. genesis stops exactly
twice: confirm interview coverage, confirm the spec.
