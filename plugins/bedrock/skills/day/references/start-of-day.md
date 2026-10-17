# Start and end of the day (D031)

The work day rolls over at the configured hour (default 10:00 local): anything before it
belongs to the previous day.

## Start of day
1. Close yesterday if it is not closed: `bedrock log closed --block <id> --at last` for each open block,
   and a one-line summary into the status note.
2. Read the newest handoff in `~/projects-memory-bank/<project>/handoffs/` and the notes it
   links. A handoff older than a later decision is "re-check before use".
3. The SessionStart context already lists stale notes and base problems; fix the stale
   ones that touch today's work first.
4. Environment: `git fetch` and `git status`; `bedrock machine`; the project's quick
   check (`bedrock cmd test-related`, or `bedrock cmd test` when the project has no quick
   one); MCP servers answer.
5. Inbox, read only: Slack DMs and mentions, GitHub reviews and failed CI, the project's
   tracker, mail when connected. Every request gets R and P and goes to the backlog with a
   link to the message (D044). A question that can simply be answered gets a copy-ready
   reply drafted in the chat, not a task. Nothing is sent: the owner sends it.
6. Summary for the owner, three lines: вчера (from commits and closed tasks), входящие (what
   needs the owner), сегодня (the next tasks in order).

Done when: the summary is sent and the backlog holds the inbox items.

## End of day
1. Every open block is paused or closed with a log line.
2. Status note: current state only, not a log.
3. A handoff if work continues tomorrow in another session (the `handoff` skill).
4. A short summary for the owner: what got done, what is left and why, the one thing
   needed from the owner, the limit spent.
5. Where the project enables it: client update draft, hours from `bedrock minutes`,
   tracker statuses (outward, so under a grant).

Done when: the summary is sent and nothing is left running.
