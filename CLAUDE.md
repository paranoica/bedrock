# CLAUDE.md

@AGENTS.md

> The **canonical** rules live in **`AGENTS.md`** (imported above) — the same file every other agent
> reads. This wrapper adds only Claude-Code-specific notes; it never duplicates AGENTS.md (duplication
> guarantees drift).

## Claude Code specifics

- **Skills** (`.claude/skills/`): **genesis** (inception/planning) · **prompt-refiner** (residue
  sharpener) · **design-creator** (visual layer) · **code-review** (audit). Route per the **Gate
  mandates** in `AGENTS.md`.
- **Fresh-context verifiers** (genesis `spec-verifier`, code-review `finding-verifier`,
  design-creator `critic`) are spawned from their skills' own instructions — no registration needed.
- **Project rules** live in `AGENTS.md`'s "Project rules" section (genesis writes them there, inline,
  so all agents share them) — **not** here.
