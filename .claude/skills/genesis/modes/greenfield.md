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
4. Fill `AGENTS.md`'s "Project rules" section **inline** (this project's canon: stack/scope/style;
   never rewrite the universal rules) per `references/canon-template.md`, and **emit per-agent
   wrappers** for the agents selected in the interview (`references/agent-wrappers.md`); emit the
   project `README.md` from `references/readme-template.md` (replace the Bedrock stub; extend a real one).
   Then emit `.github/workflows/ci.yml` from `references/ci-emit.md` (stack × project-type; refresh
   version pins once if online) **and `.github/workflows/spec-gate.yml`** (runs the deterministic gate
   in CI), and add the "Wire up CI" backlog task. Compose the project `.gitignore` from
   `references/gitignore-emit.md` (merge `common` + the stack fragment(s) + bedrock's skill-artifact
   block; never ignore a lockfile). **No `design-brief`** unless the project has a real
   visual web surface (project-type web-app/dashboard).
5. `tools/project-map/build.py <root>` — the first map.
6. The gate: `analyze_spec.py <root>` (deterministic) + spawn `spec-verifier` (fresh context) +
   `backlog.py validate`; before declaring ready, confirm the receipt is still fresh
   (`analyze_spec.py <root> --check`). Do not declare ready on a skipped **or stale** gate.
