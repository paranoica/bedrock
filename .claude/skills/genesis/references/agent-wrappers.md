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
| **Antigravity** | No (workspace rules live in `.agents/rules/`) | `.agents/rules/bedrock.md` → `@/AGENTS.md` (Always On) | Markdown + `@`-import |

## Rules

- **Single source.** Every wrapper points at / mirrors `AGENTS.md`; never restate rules in a wrapper
  (drift). Where an agent genuinely needs its own file *content* (Continue), **generate** it from
  `AGENTS.md` and mark it generated — don't hand-maintain a second copy.
- **Emit only selected agents.** Golden-default (no answer) = Claude (`CLAUDE.md`) + the shared
  `AGENTS.md`. Don't interrogate the user about six tools.
- **Antigravity — supported via a workspace rule** (verified against the official Antigravity *Rules*
  docs). Antigravity's **workspace rules** live in **`.agents/rules/*.md`** (current default;
  backward-compatible with `.agent/rules/`), are Markdown (≤12k chars), support activation levels
  (Manual / Always On / Model Decision / Glob), and support **`@`-imports**. So genesis emits a thin
  **`.agents/rules/bedrock.md`** containing just `@/AGENTS.md` (which resolves to `workspace/AGENTS.md`),
  set **Always On** — Antigravity then follows the same canonical `AGENTS.md` as every other agent.
  Antigravity does **not** read a root `AGENTS.md` as rules (the earlier secondary-source claim was
  wrong); its **global** rules file is the user-level `~/.gemini/GEMINI.md`, which genesis never touches.
- **Codex skills (verified — partly portable).** Skills are an **open standard** (agentskills.io): a
  folder with `SKILL.md` (frontmatter `name` + `description`) + `scripts/` + `references/`, loaded by
  progressive disclosure. **Codex conforms**, but discovers skills from **`.agents/skills/`** (project /
  repo / `~/.agents/skills/`), **not** `.claude/skills/`. So these skills port **in substance**, not as
  a zero-edit drop-in: move `.claude/skills/<s>/` → `.agents/skills/<s>/` and strip Claude-only
  frontmatter/placeholders (`allowed-tools`, `disallowed-tools`, `arguments`, `${CLAUDE_SKILL_DIR}`,
  `$ARGUMENTS`) — Codex doesn't document those. Subagent definitions differ per agent (out of scope for
  v1). (Codex's exact script-execution mechanism was not primary-verified.)

## Codex setup (one place)

- **Rules** — Codex reads root `AGENTS.md` natively; nothing to emit.
- **Scripts** — the genesis scripts live at `.claude/skills/genesis/scripts/` and are callable by path
  (the `spec-gate.yml` workflow does exactly this) regardless of agent.
- **Skills** — to use the consume-side skills (`prompt-refiner`, `code-review`, `design-creator`) as
  Codex `/skills`, run `python3 tools/port-skills.py <skill>`: it mirrors the folder into
  `.agents/skills/` and strips Claude-only frontmatter. **genesis runs in Claude Code — don't port
  it** (it's the inception front door and references `.claude/...` paths; other agents consume its
  output, not the skill).
