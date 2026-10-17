# The urgent path (P0, D043)

Plan, critic and cut are skipped. Secret checks, tests and linters always run.

1. **Mitigate first:** roll back to the last good version when the cause is unclear (under a
   grant), or a minimal hotfix from the production tag with a failing case and a rollback
   command.
2. **Notify the owner** if away: "P0: X down, rolled back to Y, working, cause under
   investigation" (`bedrock notify p0 ...`).
3. **Confirm:** what changed, what logs and metrics show, users no longer affected. "Fixed" is
   never said without this.
4. **Same day:** root cause with the `debug` skill, a failure note in the base, a task for the
   permanent fix at its proper risk level. The urgent fix is a patch, not the solution.

Done when: the damage is stopped and confirmed (step 3), and the same-day items exist:
the cause record, the failure note and the backlog task.
