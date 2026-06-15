# Canon template — RULES.md (+ how genesis extends CLAUDE.md)

The **universal** operating rules (which skill when, gate mandates, file-driven loop, status seam,
map-read protocol, source-of-truth hierarchy) ship in the repo-root **`CLAUDE.md`** — genesis does
**not** restate them. genesis emits **`RULES.md`** (this project's *specific* canon) and **extends**
`CLAUDE.md`'s "Project rules" section to import it.

Fill `<PLACEHOLDERS>` from the interview; **never** bake another project's choices. **Never overwrite**
`CLAUDE.md`'s universal section or an existing `RULES.md` — read and extend; surface conflicts.

(Claude-Code-only for now. `AGENTS.md` / other-agent wrappers are deferred — when added, they import
the SAME `RULES.md`, never duplicate it. That is why the project canon is a separate file.)

---
## ════ RULES.md (this project's canon — project-specific only) ════

```markdown
# <PROJECT> — canon

> This project's specifics. The universal Bedrock rules live in `CLAUDE.md`; this file does not repeat
> them. Prune ruthlessly — keep only what an agent cannot infer from the code itself.

## Stack & scope   <!-- from the interview; NEVER hardcode another project's choices -->
- Stack: <only the non-obvious; let the code show the rest>
- In MVP: <…>   ·   Explicitly out: <…>
- Code style: <indentation / file-length / naming — ASKED or DERIVED per project>

## Project-specific gate notes   <!-- optional; only where this project DEVIATES from CLAUDE.md -->
- <e.g. "the payments module is the high-risk surface → always full code-review there, never light">
```

---
## ════ Extending CLAUDE.md (genesis does this — read-and-extend, never overwrite) ════

Fill the repo-root `CLAUDE.md`'s `## Project rules` section (the `GENESIS-PROJECT-RULES` placeholder)
with:

```markdown
## Project rules
@RULES.md
> <PROJECT>: <one line — what it is and for whom>.
```

If `CLAUDE.md` already has real project rules (a re-run, or **adopt** on an existing repo), **extend**
that section; if a value conflicts with the canon, surface it to the user — do not replace it. Never
touch the universal rules above the placeholder.
