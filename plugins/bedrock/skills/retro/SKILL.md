---
name: retro
description: Weekly retro — read the week's logs, agents, reviews and failures, find what repeats, tune the system, plan a realistic next week. Use for "ретро", "итоги недели", "retro", "how did the week go".
---

# Weekly retro (Friday)

The retro changes the system, not just describes the week (D061).

## Triggers
- RU: «ретро», «итоги недели», «что улучшить»
- EN: "retro", "how did the week go", "what to improve"

## 1. Gather the numbers
- `bedrock retro --days 7`: closed blocks with minutes and estimates, open blocks, and the
  calibration factor per risk level.
- `bedrock ledger summary`: agent runs, spend, accepted results by role.
- Review records and the review noise: findings accepted or rejected by type.
- The week's failure notes and stale notes (`bedrock kb drift`, `bedrock kb validate`).
- The owner's corrections in his prompts: «не понял», «не так», «я же говорил».
- Repeated questions (`bedrock question similar`).
Done when: each source has a line in `~/projects-days/<project>/retro-<date>.md`.

## 2. Find what matters
The heaviest finding: the same failure mechanism again, which means its catcher did not catch.
Then: estimates off by more than 1.5×, agent roles that hit their cap, review types that
are almost always rejected, questions asked twice.
Done when: the findings are ranked in the retro file.

## 3. Change the system
- Small changes (thresholds, wording, a muted review type, a new FAQ card): apply, log in the
  retro file, bump the plugin version and changelog, rerun the checks.
- Structural changes (a new rule, hook or skill, a removal): one list for the owner's «го».
- A mistake becomes a failure note; a repeat becomes a rule; a broken rule becomes a check.
  Rules nobody used are removed.
Done when: every small change is logged and the structural list is sent.

## 4. Next week
One line: «реально на неделю: X, Y, Z», from the backlog by priority, sized with this week's
calibration factor.
Done when: the line is sent.

## 5. Every two weeks
Ask whether to run the architecture review. On yes, the owner types `/bedrock:arch`: the
skill runs only by his hand.
Done when: the question was asked.
