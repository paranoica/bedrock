# Canon template — filling AGENTS.md's "Project rules" (+ per-agent wrappers)

The **universal** operating rules ship in the repo-root **`AGENTS.md`** (the canonical, cross-agent
rules doc). genesis does **not** recreate them. genesis (a) fills `AGENTS.md`'s `## Project rules`
section **inline** with this project's specifics, and (b) emits thin **per-agent wrappers** for the
agents the team selected in the interview (see `references/agent-wrappers.md`).

Fill `<PLACEHOLDERS>` from the interview; **never** bake another project's choices. **Never overwrite**
`AGENTS.md`'s universal section or a real wrapper — read-and-extend; surface conflicts.

> Project rules go **inline in AGENTS.md**, NOT behind an `@import`: only Claude follows `@imports`, so
> inlining is what lets *every* agent see them. (`RULES.md` is retired — it was a Claude-only convenience.)

---
## ════ Fill AGENTS.md's "## Project rules" section (INLINE) ════

Replace the `GENESIS-PROJECT-RULES` placeholder with:

```markdown
## Project rules
> <PROJECT>: <one line — what it is and for whom>.

- **Stack:** <only the non-obvious; let the code show the rest>
- **In MVP:** <…>   ·   **Explicitly out:** <…>
- **Code style:** <indentation / file-length / naming — ASKED or DERIVED per project; never hardcoded>
- **Project-specific gate notes:** <ONLY where this project DEVIATES from the universal gate mandates
  above — e.g. "payments is the high-risk surface → always full code-review there, never light">
```

Re-run / **adopt**: extend the existing Project rules; if a value conflicts, surface it to the user —
do not replace. Never touch the universal rules above the placeholder.

---
## ════ Per-agent wrappers ════

genesis emits wrappers only for the agents selected in the interview (the agents gate). `AGENTS.md`
itself covers every agent that reads the standard natively (Cursor, Roo, Windsurf, Codex). `CLAUDE.md`
(`@AGENTS.md`) ships already. The rest (Aider, Continue, Cursor `.mdc`, …) are emitted on demand;
**Antigravity** gets a `.agents/rules/bedrock.md` workspace rule that `@`-imports `AGENTS.md` (its
global `~/.gemini/GEMINI.md` is the user's, untouched). Catalog +
exact per-agent format: **`references/agent-wrappers.md`**.
