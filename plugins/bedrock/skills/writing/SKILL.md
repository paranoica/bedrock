---
name: writing
description: Write or rewrite skills, agent definitions, briefs and rule files by the D013 rules, then check them. Use for "напиши скилл", "поправь агента", "write a skill", "edit this brief".
---

# Writing skills, agents and briefs

These texts are read by a model on every turn they load. Short and checkable beats complete
(D013).

## Triggers
- RU: «напиши скилл», «поправь агента», «перепиши бриф»
- EN: "write a skill", "fix this agent", "rewrite the brief"

## 1. Does it need to exist?
A skill exists only when a word of the owner's, or another skill, must reach it. Anything
else is a `references/` file of an existing skill, or one paragraph in one.
A user-only skill sets `disable-model-invocation: true`.
Done when: the choice (skill, reference or paragraph) is one line in the plan.

## 2. Budgets
- A model-invoked skill description: at most 60 tokens, one line, with the owner's words.
- An agent description: about twelve words.
- `SKILL.md`: at most 250 lines. A `references/` file: at most 300.
The checker enforces all of these.

## 3. How to write each step
1. English, short sentences, lists, one thought per step.
2. At most two semicolons in a sentence, at most 40 words.
3. Each step ends on a checkable completion: a file, a log line, an exit code.
   Write it as "Done when: …".
4. State the target behaviour. A prohibition stays only as a hard guardrail, next to its
   positive line.
5. One rule lives in one place. A rule a hook or a script enforces names its enforcer
   instead of restating it ("the git guard refuses …").
6. One Russian and one English trigger for each branch of the skill.
7. Paths that the text names must exist: links and backticked `references/…` paths resolve.
Done when: every step of the text has its "Done when".

## 4. A rewrite carries a rules ledger
When an existing text is rewritten, list each old rule and where it went: kept, moved (to
which file), enforced (by which hook or script), or dropped (with the reason). A `critic`
agent checks the ledger against the old and new texts, with a brief from
`templates/briefs/brief.md`.
Done when: the critic finds no rule lost without a reason.

## 5. Check
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/skillcheck.py --root ${CLAUDE_PLUGIN_ROOT} --strict`.
The root is the plugin's own folder, the one holding `.claude-plugin/plugin.json`.
It checks the frontmatter, the budgets, sentence length, semicolons, links, and the model and
effort of agents. It does not check "Done when" lines: read for them yourself.
Done when: it exits 0.

## Guardrails
- No names of people, clients or projects in a shipped text. `bedrock leaks` must pass.
- Carried text from another source keeps its licence notice.
