# Agent wrappers — what genesis emits per agent

`AGENTS.md` is the canonical rules doc and is read **natively** by most agents. genesis emits a thin
wrapper **only** where an agent needs one, and **only** for the agents selected in the interview (the
agents gate). Never overwrite a real wrapper — read-and-extend.

| Agent | Reads `AGENTS.md` natively? | Wrapper genesis emits | Format |
|-------|----------------------------|------------------------|--------|
| **Claude Code** | No | `CLAUDE.md` → `@AGENTS.md` + Claude notes (ships already) | Markdown + `@import` |
| **Cursor** | Yes (root + nested) | none needed; optional `.cursor/rules/bedrock.mdc` only if rule-type frontmatter is wanted | MDC |
| **Codex** | Yes (concatenated, closest-wins) | none for rules; MCP/model live in the user's `~/.codex/config.toml` (not emitted) | — |
| **Roo Code** | Yes (default on) | none needed | — |
| **Windsurf** | Yes (root, always-on) | none needed; `.windsurf/rules/*.md` only if `trigger`/`glob` activation is wanted | MD + frontmatter |
| **Aider** | Manual | one line in `.aider.conf.yml`: `read: [AGENTS.md]` | YAML |
| **Continue** | Unverified | generate `.continue/rules/00-bedrock.md` **from** `AGENTS.md` | MD |
| **Antigravity** | **Experimental** (secondary sources only) | `AGENTS.md` only — **NO `GEMINI.md`** | — |

## Rules

- **Single source.** Every wrapper points at / mirrors `AGENTS.md`; never restate rules in a wrapper
  (drift). Where an agent genuinely needs its own file *content* (Continue), **generate** it from
  `AGENTS.md` and mark it generated — don't hand-maintain a second copy.
- **Emit only selected agents.** Golden-default (no answer) = Claude (`CLAUDE.md`) + the shared
  `AGENTS.md`. Don't interrogate the user about six tools.
- **Antigravity is experimental.** genesis emits `AGENTS.md` only and does **not** emit or rely on
  `GEMINI.md`. The claims "Antigravity reads AGENTS.md" and "`GEMINI.md` overrides AGENTS.md" come from
  **secondary sources, not primary docs** — validate before relying; do not bake the precedence in.
- **Codex skills (not verified).** Codex's `SKILL.md` format is *nominally* the same as Claude Code's,
  so the skills here **might** port to Codex — **this is unverified**. Treat it as a near-term
  candidate that requires validation, not a fact. Subagent definitions differ per agent and are out of
  scope for v1.
