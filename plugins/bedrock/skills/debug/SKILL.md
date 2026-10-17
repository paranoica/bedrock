---
name: debug
description: Root-cause debugging — a red loop first, hypotheses, one variable at a time, a cause record, a regression test. Use first for any bug or failing test: "падает", "не работает", "почему", "CI красный".
---

# Debugging to the root cause

A fix without a confirmed cause is a patch (D048). Every step ends on a check.

## Triggers
- RU: «баг», «не работает», «почему падает», «CI красный»
- EN: "bug", "it's broken", "why does it fail", "CI is red"

## 0. Check the plug
Right branch, deployed version, environment, data, config. Read the module's failures (F) and
pitfalls in the knowledge base (`bedrock kb backlinks <module>`).
Done when: each is confirmed or the mismatch is the answer.

## 1. The report
Expected (from its source: spec or decision), actual, how to reproduce.
Done when: the three are written in `~/projects-days/<project>/<date>/<block>/debug.md`.

## 2. A red loop before any theory
One command that goes red on this exact bug, picked from `references/loop-ladder.md`.
Tighten it: fast, sharp (it asserts the exact symptom), deterministic. A flaky bug first
raises its reproduction rate. `bedrock log debug-start --block <id>`.
No loop possible: stop, list what was tried, one ask to the owner.
Done when: the loop command is in `debug.md` and it fails for the right reason.

## 3. Reproduce exactly and minimise
This bug, not a nearby one; strip it until every element is load-bearing.
Done when: the minimal case is in `debug.md`.

## 4. Hypotheses
3–5 ranked, falsifiable: "if X, then changing Y turns the loop green". Earlier failed fixes
enter as hypotheses with what they showed. Send them to the owner as information, not a gate.
Done when: the list is in `debug.md`.

## 5. Experiments
One variable at a time: debugger or REPL first, then targeted logs tagged `[DEBUG-<id>]`.
Never log everything and grep. Performance: a baseline, then bisect. The experiment log
records every hypothesis with its result (negative ones count) and every environment change.
`bedrock log debug-loop --block <id> --detail "<hypothesis> → <result>"`.
Done when: one hypothesis is confirmed by the loop.

## 6. The cause record
Five lines in `debug.md`, shaped as in `references/cause-record.md`: symptom, seen (all n
occurrences, "explains k/n", and k<n is not yet the cause), rule broken, elsewhere, change.
`bedrock log debug-cause --block <id> --ref <path of debug.md>`.
Done when: the record explains n/n. An implementer brief points `Cause:` at it.

## 7. Regression test and fix
- The test sits at a correct seam and is red for the right reason; no seam is an
  architecture finding, not a reason for a shallow test.
- Fix in the shared place, for every caller; never change config or fixtures to go green.
- Done only when the original scenario no longer reproduces, the loop is green on all n
  occurrences, and the full suite passes (`bedrock cmd test`).
Done when: all three hold.

## 8. Clean up
No `[DEBUG-` left (`git grep -n '\[DEBUG-'` is empty); harnesses kept in the block folder;
the commit states the confirmed cause. `bedrock log debug-done --block <id>`.
Done when: the grep is empty and the `debug-done` line exists.

## 9. Learn
A failure note (F) in the base with the `kb` skill; "Elsewhere" becomes backlog tasks; a
recurring pattern becomes a rule or a check.
Done when: the note exists and `bedrock kb validate` is clean.

## Fuses
- Two failed fixes on one symptom: start this flow from step 0.
- The same command with the same error three times: stop and re-hypothesise.
- Hypotheses exhausted: a fresh view, the `escalation` agent, or a fresh session with a
  handoff. The agent's brief comes from `templates/briefs/brief.md`: the task, what was
  tried and why it failed go into Task and Known.
