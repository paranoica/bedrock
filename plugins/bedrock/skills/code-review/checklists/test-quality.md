# Test-quality & coverage checklist

"Has tests" is not "is tested". This checklist judges whether tests actually constrain
behavior, and whether the *changed* lines are covered. Read on any diff that adds logic
or claims test coverage. Overlaps llm-slop (generated tests are often hollow) — flag once.

## Diff-coverage (the lines that changed)
- **Are the changed/added lines exercised by any test?** New branch, new function, new
  error path with no test that hits it = effectively untested, regardless of overall
  coverage %. This is the metric that matters for a PR, not project-wide coverage.
- **New conditional logic** (if/else, switch, error handling) where only the happy path
  is tested — the branch that matters (the failure/edge) is the untested one.
- **Bug fix with no regression test** — the bug can silently come back. A fix PR that
  doesn't add a test reproducing the bug is incomplete.

## Tests that don't actually test
- **No meaningful assertions:** the test runs the code but asserts nothing, or asserts
  something trivially true (`assert True`, `expect(x).toBeDefined()` on something that
  can't be undefined).
- **Asserting the mock, not the behavior:** the test verifies "the mock was called"
  instead of "the output/effect is correct". Tautological.
- **Mocking the thing under test:** stubbing the very function/module being tested so the
  test can't fail. Common in generated tests.
- **Over-mocking:** every collaborator mocked so the test exercises no real integration —
  passes even when the wiring is broken.
- **Snapshot tests of nothing meaningful**, or snapshots blindly updated so they assert
  the current (possibly buggy) output.
- **Tests that can't fail:** comment out the implementation — would the test still pass?
  If yes, it's not a test. (This is a quick mutation-style sanity check; apply it mentally
  to suspicious tests.)

## Weak / risky test design
- **Flaky-by-construction:** depends on real time/`now()`, real network, `sleep`,
  ordering of dicts/sets, random without a seed, shared mutable global state between tests.
- **Non-deterministic assertions** (asserting on unordered output as if ordered).
- **Hidden coupling between tests** (test B only passes if test A ran first).
- **Testing implementation details** so brittle that any refactor breaks them without a
  behavior change — the inverse failure (still flag, but LOW).

## Removed / weakened tests (tie-in to removed-defenses)
- **Diff deletes or `skip`s a test** — why? A removed test alongside a code change is a
  red flag; the test may have been failing because the change is wrong.
- **Assertions loosened** (tightened `==` turned into a looser matcher, error case turned
  into a no-op) to make a failing test pass.

## Critical paths that demand tests
Auth, authorization, payments, money math, data deletion, migrations, anything in the
severity-rubric's "catastrophic impact" set — these should have tests, and the absence
is a MEDIUM+ finding, not a nitpick.

## What NOT to flag
- Missing tests on trivial, side-effect-free glue or pure config.
- Reasonable use of mocks at true external boundaries (third-party APIs, clock) when the
  core logic is still really exercised.
- Mature test suites with a deliberate, documented testing strategy you're second-guessing
  on taste.
- Exploratory/throwaway scripts not part of the shipped product.
