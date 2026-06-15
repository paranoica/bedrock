# Mode: greenfield

Empty / near-empty repo; the user wants to **start** a project.

**Detect:** no `docs/decisions.md`, no `genesis.tasks.json`, little or no source. (If code or a
`CLAUDE.md` already exists but there is no canon/spec/map → that is **adopt**, not greenfield.)

**Run the full pipeline** (see `SKILL.md`): preflight → adaptive interview → spec `docs/` → backlog →
canon → first map → spec-analyze gate → archive. Two stops only (confirm interview coverage; confirm
the spec).

Sequence for the generation half (after the spec is confirmed):
1. Write anchored `docs/` from `references/spec-templates/` (every domain noun → a `term:` anchor;
   unknowns → `TODO(decision:)` in open-questions).
2. Write the backlog roots into `genesis.tasks.json`, then `backlog.py stamp` (fills closures + hashes,
   renders `PLAN.md`).
3. `calibration.py snapshot` (baseline for future replans).
4. Emit `RULES.md` (project canon) and **extend** the shipped root `CLAUDE.md`'s "Project rules"
   section (`@RULES.md`; never rewrite its universal part) per `references/canon-template.md`; emit
   the project `README.md` from `references/readme-template.md` (replace the Bedrock stub; extend a
   real README).
5. `tools/project-map/build.py <root>` — the first map.
6. The gate: `analyze_spec.py <root>` (deterministic) + spawn `spec-verifier` (fresh context) +
   `backlog.py validate`. Do not declare ready on a skipped gate.
