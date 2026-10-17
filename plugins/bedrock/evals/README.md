# Skill evals

One folder per case: `prompt.md` (the owner's words) and `graders/` (a `tool_used` grader that
the right skill fired, or did not, plus an `llm` grader on the behaviour).

Run with a Sonnet judge. The default Haiku judge failed Russian replies that met the criteria:

```
claude plugin eval plugins/bedrock --judge-model sonnet --no-publish --max-cost-usd 2
```

Add `--case <glob>` for one case, `--runs 1` for a quick check. Results land in `results/`,
which git ignores. The cases run without a project, so the skills cannot read real state;
the bench (P7) adds cases that run against a scaffolded project.
