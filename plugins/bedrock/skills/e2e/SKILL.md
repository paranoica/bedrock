---
name: e2e
description: End-to-end checks in a headless browser — scripted Playwright tests for main paths, and an exploratory run that turns findings into tests. Use for "прогони e2e", "проверь в браузере", "e2e", "test the UI".
---

# End-to-end in a real browser

E2E tests assert what the user gets, never that a selector exists (D049).

## Triggers
- RU: «прогони e2e», «проверь в браузере», «пройди сценарий»
- EN: "run e2e", "check it in the browser", "walk the flow"

## 0. Tools
Scripted tests need the project's Playwright dev dependency. Exploratory mode needs the
Playwright MCP server. Both are installed only on the owner's word. Without them, say what is
missing and stop here.
Done when: `npx --no playwright --version` runs (`--no` keeps npx from downloading it), or
the gap is reported.

## 1. Scripted tests (in the project, run in CI)
- Cover login and the main user paths first.
- Locators by role or test id, never by CSS structure.
- Assert outcomes: the saved record, the total shown, the file downloaded.
- Clean state per run: a test user, fresh data, stored auth from a setup project.
- A trace on failure (`trace: "retain-on-failure"`).
- Run through `bedrock cmd e2e`, so the heavy-run lock applies.
Done when: the new test fails before the change it guards and passes after.

## 2. Exploratory run (Playwright MCP)
1. Start from a clean state with a test user.
2. Walk the flows the plan names. Try odd input, the back button, a double submit, a slow
   network, a narrow window.
3. For UI work: screenshots at 375, 768 and 1280 px; the flow by keyboard only; an axe scan.
4. Every break found becomes a scripted test from step 1, then goes to the `debug` skill.
Done when: each finding has a scripted test or a reason it cannot have one.

## 3. Report
What was checked, on which environment, with what result: the command and its output, or
the screenshot paths. A check that did not run is named as not run.
Done when: every flow in the plan has a result or a "not run" line.
