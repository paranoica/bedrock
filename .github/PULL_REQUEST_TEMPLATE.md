<!-- Bedrock template PR template. Edit freely once genesis has shaped your project. -->

## What & why
<!-- One or two sentences. Link the task(s) / decision(s) this implements. -->
- Implements:  <!-- e.g. T012, decision:auth-model -->

## Checklist
- [ ] Scope matches the task's `acceptance` (no extra, unrequested work).
- [ ] Touched only the task's `files` (or explained why not).
- [ ] Spec is still the source of truth — if a decision changed, `docs/` was amended and the backlog
      re-derived (`backlog.py re-derive`), not hand-patched.
- [ ] The right gate ran for the risk: design → design-creator · code audit → code-review loop.
- [ ] Task state updated via `backlog.py` (not by hand-editing `PLAN.md` / `genesis.tasks.json`).
- [ ] `bash tools/run-evals.sh` passes (if you changed the template's own tooling/skills).

## Notes for the reviewer
<!-- Risks, trade-offs, anything you want a second pair of eyes on. -->
