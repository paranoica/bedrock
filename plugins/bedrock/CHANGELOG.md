# Changelog

## 0.2.1
- The session start names the bedrock agent roles to use (inventory, researcher, implementer,
  reviewer) and keeps general-purpose, which runs on the session's own model, for work no role
  fits; the `day` skill says the same for the plan's agents list.

## 0.2.0
- Hooks refuse one thing only: `gh pr create` and `gh pr merge` without a review of the head
  commit. Every other guard is gone: git, push, secrets and `.env`, outward actions, installs,
  MCP writes, `~/.claude`, heavy runs, the bench answer key, agent briefs, files and budgets.
- Grants are gone with them: `/bedrock:allow`, `/bedrock:unleash`, `/bedrock:revoke`, grant
  words and spend modes. Outward steps go on the owner's word in the conversation.
- `bedrock review pass` needs `--agent <id>`: a reviewer agent of the same session that
  finished after the branch's last commit. The record keeps the reviewed commit; a later
  commit voids it. Records written before 0.2.0 are not accepted.
- The red-CI merge check is gone (some projects have a check that is always red).
- If bedrock cannot load, work goes on; only the review gate refuses.
- `bedrock agents` replaces the agent ledger: runs by role, model, day or project, read from
  Claude Code's own transcripts, with a line saying how many it could not read. The ledger
  hook recorded no real run: a background agent is listed among its own running tasks, so
  the hook held it at the stop until Claude Code cut it off.
- No desktop notifications from hooks any more (end of turn, questions, Claude Code's own
  prompts). `bedrock notify` stays for an explicit call, such as the night mode's P0.
- The Stop hook no longer holds the session for the knowledge base; uncommitted notes and
  stale notes are reported at the next session start, which also names the working loop.
- The project settings `agents` and `bench.answer_key` are still accepted but nothing
  enforces them.

## 0.1.3
- The spend mode switches only on a command: a question ("не потратим?"), a negation
  ("не тратим") or a longer word ("потратим") no longer turns on max spending.

## 0.1.2
- Writes on the `telegram` MCP server skip the grant gate and are confirmed by the native
  `permissions.ask` rule instead; agents are still refused.

## 0.1.1
- Grants are written through a unique temp file, so a read-only stub the sandbox leaves at a
  denied path cannot block them.
- The leak check's `allow` list also exempts listed names in that repository.
- The status line measures a session past its compact window against the real window.
- The night watchdog lifts Claude Code's Stop-hook block cap for its session.
- design-creator finds its render libraries outside the plugin folder; `bedrock doctor` checks
  them and the transcription environment.
- humanize is the owner's tuned skill, with the text check added.
- code-review studies the repo's defenses first, holds security findings to an exploitability
  bar, and may probe the project's own functions in isolation.
- doc keeps the Markdown beside the PDF and lets the owner pick the style.

## 0.1.0
- First release of bedrock v2.
