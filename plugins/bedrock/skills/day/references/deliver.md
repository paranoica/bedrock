# Delivering a change (D052, D053)

1. **Branch** `type/slug`, with the task id when there is one; the client's conventions win
   in a client repository.
2. **Pull request** = one block; over ~400 changed lines it splits into stacked PRs. It opens
   only after both reviews passed (the git guard checks `bedrock review pass`). Description from
   intent: why (link), what changed, how it was verified (live evidence), risk, where to look
   closer, out of scope. Project engineer's voice; the leak check runs on the text.
3. **Push, PR, merge, deploy** each need the owner's grant; the guard asks for it. Merge only
   with green CI and passed reviews.
4. **Live verification** after a deploy: a short read-only smoke of the critical paths (at
   most ~5 minutes), the feature itself, permissions on touched endpoints; results, not
   selectors. Evidence goes in the report: the command and its output, or a screenshot.
5. **Failure** stops and reports; rollback only under a grant.
6. CI is read once after a push; red CI goes to the `debug` skill.

Done when: the PR is open with green CI and passed reviews and the live check is in the
report with its evidence. Short of that, the report says plainly what was not checked live,
or names the outward step that waits for the owner's grant.
