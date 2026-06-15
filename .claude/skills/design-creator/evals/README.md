# Evals — catching regressions after edits

A lightweight harness to check that a change to the skill didn't quietly break something it used to do well. Not a CI rig — a repeatable manual check the author (or the engine) runs after editing the skill.

## What's here

- `golden-briefs.json` — a small, deliberately varied set of briefs that exercise the axes (mode × family × deliverable-type × domain-fit × perf budget). Each is chosen to stress a specific rule.
- `rubric.md` — the pass/fail criteria each output is graded against, mapped to the invariants.

## Deterministic self-tests (no model, run anytime)

Two tools ship a zero-dependency `selftest` that guards their math — run them after touching either:

- `node evals/diversity.mjs selftest` — the spread metric flags a clustered set and passes a varied one.
- `node tools/calibration.mjs selftest` — the critic-calibration Brier + `--kind` filter compute correctly (guards the critic feedback loop wired into the QA gate).
- `node tools/contrast.mjs selftest` — the WCAG contrast math + the token-classify floor check (the layer-1 contrast pre-check the engine runs at token-lock).

A third eval is **render-backed** (needs a browser; self-skips cleanly otherwise):

- `node evals/motion.mjs` — runs the `tools/verify.mjs` motion pass on fixtures and asserts the verdicts have teeth (an inert page FAILs `motion_non_inert`; a page that ignores `prefers-reduced-motion` FAILs `reduced_motion_respected`). Run after editing the motion thresholds or the scroll/measure logic in `verify.mjs`. Wired into `tools/run-evals.sh`, browser-gated.

## How to run (Claude.ai / no-subagent flow)

For each brief: read `index.json` + `invariants.md`, then follow the skill to produce the deliverable (or a mockup). Grade the output against `rubric.md` — every rubric line is yes/no, the same discipline as the QA gate. Record fails. A regression is any rubric line that passed before an edit and fails after.

In Claude Code / Cowork (subagents available), the skill-creator's `run_eval.py` / eval-viewer flow can automate the runs and the description-triggering test; this folder's briefs and rubric feed straight into it.

## When to run

After any edit to a MUSTHAVE rule, the QA gate, the router, or the invariants. The point is to make the floor *measurable over time*, not to re-litigate taste.

## The regression gate (champion-beating, not just "different")

Rubric pass/fail catches floor regressions. It does **not** catch a rule edit that makes output
merely *other* instead of *better* — that's what `tools/tournament.mjs` is for, and it only works
once it has a champion to beat. Seed and run it like this:

1. **Seed a champion (once per brief).** Take the current best output for a brief, give it a stable
   id (e.g. `clean-saas-v2`), and log at least one pairwise win for it so it has an Elo rating:
   `node tools/tournament.mjs match clean-saas-v2 <baseline-id> --brief clean-saas-landing`.
2. **After a rule edit**, regenerate that brief into a new id (`clean-saas-v3`), run the critic
   (or owner) pairwise vs the champion, log the result, then gate:
   `node tools/tournament.mjs regression clean-saas-v3 clean-saas-v2 --brief clean-saas-landing`
   → `PASS` ships the change; `REGRESSION_BLOCK` means the edit made it different, not better — rework.
3. **Negative briefs** (`negative: true`) go through the same loop, but the champion is the
   *restrained* exemplar — a more spectacular candidate must LOSE. This is how the tournament
   guards against over-ambition creep, not just slop creep.

The rubric is the floor; the tournament is the bar. Run both after a MUSTHAVE/gate/invariant edit.
