# Implementing one task (D039, D022)

1. **Test first.** A blind test (written from the spec, not from code) for the task; run it
   and see it fail on the current code. A test green before the change checks nothing.
   Expected values come from the spec or the correct answer, never from what the code returns.
2. **Minimal code** to turn it green; verify after each function or every two or three edits.
3. **Refactor only while green.** Of two versions that pass, the one with less code wins
   (D051): needed at all → reuse → standard library → native feature → installed dependency
   → minimum code.
4. **Automatic checks** run on every edit (format and lint hook) and before the commit
   (`bedrock check`, `bedrock leaks`, enforced by the git guard).
5. **Read the diff yourself** against the plan; run the task's tests yourself. An agent's
   "done" is never taken on its word.
6. **Commit** the task: one line `type(scope): description`. The commit is the rollback point.

## When it fails
- Red after the first fix: a second attempt with new information.
- Red again: the `debug` skill, cause first.
- A failed attempt is set aside (stash or a branch), never reset destructively; other work
  stays untouched.

## Agents for implementation
- Only with a brief from `templates/briefs/implementer.md` (the hook requires Task, Done when,
  Cause, Files, Report).
- Heavy tests through `bedrock test` or `bedrock cmd` (the heavy-run guard refuses others).
- At most two runs per task; after that the session takes it (D007).
