---
name: hunt
description: Bug hunter — try to break code that is already green, with properties, boundaries, hostile input and concurrency. Use for "сломай это", "поищи баги", "break it", after green on R2/R3.
---

# Bug hunt

Green tests prove the cases someone thought of. A hunt looks for the ones nobody did (D049).

## Triggers
- RU: «сломай это», «поищи баги», «что тут может упасть»
- EN: "break it", "hunt for bugs", "what could go wrong here"

## When it runs
- Always on R3 blocks and on files inside the project's `critical_zones`.
- Briefly on R2, after the block's tests are green.
- On the hottest modules (`bedrock arch hotspots`) when the architecture review runs.
Done when: the block's plan says which of these applies.

## 1. Brief the hunter
Start the `bug-hunter` agent with a brief from `templates/briefs/brief.md`:
- Task: the module and the spec it must meet (plan done-when, decisions, module note).
- Read: the code and its tests, in order.
- Known: the cases the tests already cover.
- Commands: the project's test command through `bedrock cmd`.
Done when: the agent's report file exists.

## 2. What the hunter tries
1. **Properties from the spec**, not from the code: Hypothesis in Python, fast-check in TS.
   Examples: a round trip returns the input, a sort keeps every element, a total never goes
   negative. The libraries are dev dependencies, added only on the owner's word.
2. **Boundaries:** empty, null, zero, max, one past max, the first and the last element.
3. **Hostile input:** injection strings, huge input, odd unicode, wrong types.
4. **Concurrency:** the same request twice at once, a replay, a kill mid-run.
5. **Scale:** the data volume the plan's Scale section names.
6. **Metamorphic checks** for text and extraction systems (the domain pack names them):
   a paraphrase keeps the result, an added negation never yields a positive fact, a
   relative's condition is not the subject's, document order does not change the facts, and a
   fact split across a chunk boundary is still found.
Done when: each tried technique is listed in the report with its result.

## 3. Every finding is checked
1. Minimise it to the smallest failing input.
2. A `verifier` agent re-runs it from scratch. Agent-written property reports are often
   invalid: only a reproduced failure counts.
3. Confirmed → the `debug` skill, cause first. Spec ambiguity → one question to the owner.
Done when: each finding is reproduced and routed, or cut with the verifier's reason.

## 4. Keep what it found
A confirmed finding leaves a regression test at the right seam (the `debug` skill does this)
and, when it is a pattern, a line in the domain pack or a failure note in the knowledge base.
Done when: each confirmed finding has its test or its note.
