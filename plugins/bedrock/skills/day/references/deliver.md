# Delivering a change (D052, D053)

1. **Branch** `type/slug`, with the task id when there is one; the client's conventions win
   in a client repository.
2. **Pull request** = one block; over ~400 changed lines it splits into stacked PRs. It opens
   only after both reviews passed (the review gate checks `bedrock review pass --agent`). Description from
   intent: why (link), what changed, how it was verified (live evidence), risk, where to look
   closer, out of scope. Project engineer's voice; the leak check runs on the text.
3. **Push, PR, merge, deploy** go on the owner's word in the conversation; no command is needed. Merge
   only with passed reviews, and with green CI unless the project names a check known red.
4. **Live verification** after a deploy: a short read-only smoke of the critical paths (at
   most ~5 minutes), the feature itself, permissions on touched endpoints; results, not
   selectors. Evidence goes in the report: the command and its output, or a screenshot.
5. **Failure** stops and reports; rollback on the owner's word.
6. CI is read once after a push; red CI goes to the `debug` skill.

Done when: the PR is open with green CI and passed reviews and the live check is in the
report with its evidence. Short of that, the report says plainly what was not checked live,
or names the outward step that waits for the owner's word.
