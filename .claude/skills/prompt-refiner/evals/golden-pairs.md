# Golden pairs — the residue-gate regression (judgment, not script)

The residue-gate is a **judgment**, not a script (mechanizing "which engine does this resolve to?"
over free text would be a lying mechanism). So its regression is this golden set: each pair has one
side that an engine can start as-is (→ engine, refiner silent) and one side that does not (→ residue,
refiner takes). Re-read and self-check against these after any change to `residue-gate.md`. The rule:
if your verdict ever puts refiner on a side an engine could start, the test leaked — fix the test.

Test by the criterion **"does it resolve to one engine that can start as-is?"** — never by topic.

| # | Request | Resolves to one engine that can start? | Correct verdict |
|---|---|---|---|
| 1a | "make the button nicer" | yes — button exists → dc-edit/direct; dc surveys | dc · silent |
| 1b | "do something about onboarding, it's bad" | no — doubles dc/code/copy; no target | residue → refiner |
| 2a | "why does `test_auth.py::test_expired` fail" | yes — locatable code → code-review/debug | code-review · silent |
| 2b | "everything's slow, take a look" | no — which flow? measured where? | residue → refiner |
| 3a | "I want to launch a storage-rental service" | yes — inception → genesis interviews | genesis · silent |
| 3b | "this whole thing is a mess, sort it out" | no — which engine? what target? what's done? | residue → refiner |
| 4a | "make the landing punchier" | yes-ish — resolves to dc; vague *inside* → dc surveys | dc · silent (default-yield) |
| 5a | "add a reviews section" — **managed** project (`docs/`+`genesis.tasks.json`) | yes — feature → **genesis replan** (spec+backlog) | genesis · silent |
| 5b | "add a reviews section" — **non-managed** repo | no managed backlog → refiner sharpens + routes | residue → refiner |

Pairs 5a/5b are the **same phrase**, split only by managed-ness — the proof that managed-ness belongs
in the criterion, not as a side note.

## The asymmetry to preserve
On a borderline row, the correct default is the **silent** side (yield). A wrong "silent" is cheap
(the engine asks its own question); a wrong "take" is a false interception (an extra round of
questions for nothing). Calibration (`scripts/calibration.py`) tracks `false_interception` as the
costly error — a rising count means the gate is leaking and the test needs tightening.
