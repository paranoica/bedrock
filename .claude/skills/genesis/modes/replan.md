# Mode: replan — re-derive the backlog when the spec changes (including new spoken work)

The spec changes in two ways; replan handles **both**, then re-derives the backlog **without losing
done work**. Never hand-patch a frozen plan — the spec is the source; re-derive from it.

## Step 0 — which trigger? (this is the step that was missing)

- **The spec already changed** — the user edited `docs/`, or a decision was overturned → go to Step 1.
- **New work is requested in words** — a feature spoken, e.g. routed here by **prompt-refiner**
  ("add a reviews section"). The spec has **not** changed yet, so there are no changed anchors to
  re-derive from. **Amend the spec first:**
  1. **Targeted interview on the delta only** (not the whole project): the new feature's scope, the
     decision(s) it introduces, any new domain terms. Same discipline as the main interview — never
     invent; unknowns → `TODO(decision:)` in `open-questions.md`.
  2. **Write + anchor** the new decision(s)/term(s) into `docs/` via `spec-templates/` (every domain
     noun → a `term:` anchor). These newly-written anchors are the "change" that Step 1 re-derives from.

  Only after the amend do the steps below have anything to act on. (This is why a feature routed from
  refiner lands here and not in code directly — it enters through the spec + backlog, never around them.)

## Step 1 — classify the flips, and read the accumulated signal
`calibration.py classify` — `new-decision` / `open-question-resolved` are NEUTRAL; `settled-overturned`
is a candidate, recorded `charged=false` (enters the interview bar only if a human later `tag`s it).
Then **`calibration.py report` — read it before re-interviewing**: a non-zero `interview_bar_signal`
(human-tagged "should've-been-caught" misses) means dig deeper on those axes this time. This is the
loop's consumer — the signal is produced **and read**, not write-only telemetry.

## Step 2 — see the impact (dry-run)
`backlog.py re-derive` — which tasks drift (→ `needs-review`, soft) vs structural change (→ `stale`,
re-derive them). On a new-work amend, the new anchors surface as additions → new tasks to add. Review.

## Step 3 — apply
`backlog.py re-derive --apply` — persist the **statuses**. `done` is never silently un-done: a drifted
`done` becomes `needs-review`, not gone.

## Step 4 — address
Re-derive `stale` tasks (re-trace to the new/renamed anchors); add tasks for new anchors; confirm each
`needs-review` still holds, then clear it via `backlog.py status <id> <state>`. If the **stack** changed,
re-emit `.github/workflows/ci.yml` and the project `.gitignore` to match (`references/ci-emit.md` /
`references/gitignore-emit.md`).

## Step 5 — re-baseline
`backlog.py stamp` — refresh closures + hashes. `calibration.py snapshot` — new baseline.

## Step 6 — gate
`backlog.py validate` + `analyze_spec.py` + `spec-verifier`, before declaring ready.
