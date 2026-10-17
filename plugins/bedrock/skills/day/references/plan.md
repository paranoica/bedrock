# Plan template (D035)

```
# <task>

Risk / priority: R<n> P<n> — <why>
Done when: <a test, a command or a number>
Stands on: <decision links>

## Assumptions
<everything decided without asking, one line each, so a wrong guess is visible>

## Scale
<data volume and load the code must hold>

## Files
<the files this plan changes>

## Tests
<test name — what it asserts — where the expected value comes from (the spec)>
<edges: empty, null, boundary and one past it, first and last, hostile input, concurrency,
 the side that must not change>

## Tasks
| id | task | files | test | who (model) | estimate |
|---|---|---|---|---|---|

## Agents
<role × runs, critic and review rounds included; the total is `agent_budget`>

## Estimate
<minutes by steps × the calibration factor for this risk level (D041)>

## Out of scope
<what this plan does not touch>
```

R3 adds:

```
## Design
<mechanism, interfaces, two or three options with the rejected ones and why, risks>

## New decisions
<decisions to record in the knowledge base before any code>
```

Rounds: v1, critic, v2, never a v3; a failing v2 means the task is misunderstood and goes
to the owner.
