# Changelog

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
