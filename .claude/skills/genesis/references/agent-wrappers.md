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
- **Antigravity is experimental — re-checked, still NOT primary-verified.** Confirmed from a primary
  source (Google Codelab): Antigravity uses `.agents/` (`.agents/agents.md` for team **personas**, plus
  `skills/`, `workflows/`). The claims that Antigravity reads a **root `AGENTS.md` as a rules file**
  (since v1.20.3) and that **`GEMINI.md` overrides `AGENTS.md`** are consistent across secondary sources
  (agentpedia et al.) **but cite no official docs**; the official rules page
  (`antigravity.google/docs/rules-workflows`) is JS-rendered and could not be fetch-verified, and the
  only readable primary source shows the persona file `.agents/agents.md` — **not** root
  `AGENTS.md`-as-rules — so the two may be conflated. genesis emits `AGENTS.md` only and **never** emits
  or relies on `GEMINI.md` (so nothing of ours overrides anything). **To graduate to supported:** confirm
  the root-`AGENTS.md`-as-rules behaviour in the official docs (open the JS-rendered page in a browser).
- **Codex skills (not verified).** Codex's `SKILL.md` format is *nominally* the same as Claude Code's,
  so the skills here **might** port to Codex — **this is unverified**. Treat it as a near-term
  candidate that requires validation, not a fact. Subagent definitions differ per agent and are out of
  scope for v1.
