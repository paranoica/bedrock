---
name: review
description: Review gate for a finished block — deterministic checks, code review, plan-compliance review, silent fixes, rounds until clean. Use for "проверь", "ревью", "review this", before any PR.
---

# Review gate

Every real finding is fixed; imaginary ones are rejected with evidence (D050, D051).

## Triggers
- RU: «проверь», «сделай ревью», «посмотри что получилось»
- EN: "review this", "check the change", "is it ready"

## 0. Scale to risk
The block's level comes from the plan (D032). Critical-zone globs in the project settings
raise it to R3 whatever the plan says.
- R1: step 1, then a quick read of the diff by the session. Skip to step 5.
- R2: steps 1 to 5, one reviewer agent.
- R3: steps 1 to 5, the reviewer and the `security-reviewer` agent, both at high effort.
- Every agent here gets its brief from `templates/briefs/brief.md`.
Done when: the level and its reason are one line in the block's plan, or in its `taken` log
line for R1, which has no plan.

## 1. Deterministic checks first
Run `bedrock check --base <base>` and `bedrock leaks`, then the project's linters and types
through `bedrock cmd lint` and `bedrock cmd typecheck`. Fix what they report before any model
reads the diff. The model gets their output and does not repeat it.
Done when: all exit 0, or each remaining line is a recorded false positive.

## 2. Code review
Run the `code-review` skill in uncommitted or PR mode on the block's diff. It brings
security, correctness and performance, plus the code rules of D022: AI slop, needless
abstraction, test tampering, duplicates.
- Each finding carries a code line, a failure scenario and a confidence. No scenario, no
  finding.
- The reviewer checklists of the project's packs (`packs` in its settings, files in the
  plugin's `packs/`) are part of the review.
- HIGH and CRITICAL go through its verifier step before anything is fixed.
Done when: its report passes `check_report.py` with a receipt.

## 3. Plan-compliance review
A `reviewer` agent with a brief from `templates/briefs/brief.md`. It gets the plan, the
block's done-when, the decisions it rests on, and the diff. It answers three questions:
1. Is every requirement of the plan done, with a test for each edge case it names?
2. Did anything outside the plan's files or scope change?
3. Does the diff contradict a decision or a module note covering these files (D026)?
Done when: the agent's report lists each requirement as done, missing or out of scope.

## 4. Fix, from the cause
- Fix every real finding, LOW and cosmetic included, without asking (D050).
- Reject an imaginary one with its evidence: a null check where null cannot arrive, an
  abstraction with one implementation, a test for an impossible case.
- A fix starts from the cause (`debug` skill for anything that is not obvious), never a patch
  over the symptom. A new test for a fix is red before the fix.
- Prove the test guards the fix: put the old line back for a moment, the test must fail,
  then restore it. Run Python this way with `PYTHONDONTWRITEBYTECODE=1`, or a cached `.pyc`
  of the old line can keep the run green. A test that stays green guards nothing: rewrite it.
- Record each outcome with the code-review skill's `scripts/record_outcome.py tp|fp`, so
  types that are almost always rejected get muted at the retro.
Done when: every finding is fixed or rejected with a reason in the report.

## 5. Re-review only the fixes
- Each next round reviews only the previous round's fixes, plus the sibling paths of each
  fix: the same kind of input reaching another entry point (a guard fixed for one command
  is checked for the other commands that take the same input).
- Stop when a round finds nothing real.
- Real findings not falling between rounds mean the design is wrong: back to the plan or the
  `debug` skill, a fresh view if needed.
- Fuse: five rounds, then stop and tell the owner what keeps coming back.
Done when: the last round is clean, then `bedrock review pass <branch> --notes "<summary>"`.
The git guard refuses a PR without this record.

## 6. Tell the owner
One line in Russian, nothing more unless asked:
`ревью: 9 замечаний, 7 исправлено, 2 отклонено (мнимые)`.
A finding the owner must decide on (a product choice, an accepted risk) is the one question
of the message, with a default.
Done when: the line is sent.

## Guardrails
- Review records are self-attested (`bedrock review pass`). Record a pass only after the last
  round is clean.
- The reviewer agents never edit, commit or push. The session applies every fix.
