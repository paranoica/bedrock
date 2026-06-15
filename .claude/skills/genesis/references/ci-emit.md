# CI emitter — genesis writes the project's CI workflow

genesis emits a **real, working** GitHub Actions workflow at `.github/workflows/ci.yml` — like it
emits `docs/` and the canon. **No AI runs in CI:** it is plain GitHub jobs (lint / test / build) that
GitHub executes on its own runners. genesis writes it **once** at project creation (and on `replan`
only if the stack changes); the **only** network use is an optional one-time refresh of version pins
at generation.

## Selection — by stack × project-type

Pick the prototype from `ci-templates/` by the project's **stack** (from `AGENTS.md` → "Project rules"
→ Stack) and the **project-type** (the interview's project-type gate):

| Prototype | Stack |
|-----------|-------|
| `node.yml` | Node / TypeScript |
| `python.yml` | Python |
| `go.yml` | Go |
| `rust.yml` | Rust |
| `generic.yml` | anything unrecognized — a skeleton + TODO (never a fake-green CI) |

**project-type tunes the steps** (it does NOT change the lint/test parts):
- `library` / `cli` → keep the **build/package** step (wheel + sdist, binary, crate, `pnpm pack`).
- `web-app` / `service` → keep `build`; drop packaging.
- `worker` → test + build, no package.

## Parametrize (never hardcode another project's choices)

Fill `<PM>` (pnpm/npm/yarn), the runtime version (`<NODE>`/`<PY>`/`<GO>`), and the lint/test/build
commands from the project's stack. **Drop steps the project doesn't have** (e.g. no `typecheck` if it
isn't TypeScript; no `mypy` if not configured). Match the package manager — remove the pnpm setup for
an npm/yarn project.

## Version pins (the one-time network use)

At generation, optionally refresh the pinned versions (runtime + `actions/*@vN`) to current stable —
**one** network call. **Offline → keep the prototype's defaults and leave a `# verify pins` comment.**
After generation no network is needed; GitHub runs the workflow itself, mechanically.

## The backlog task (CI is tracked, not just dropped)

genesis adds a task to `genesis.tasks.json` so "make CI green" is a checkable unit, not an unverified
artifact:

```jsonc
{
  "id": "T0xx", "title": "Wire up CI (.github/workflows/ci.yml)", "sprint": "S1", "status": "todo",
  "spec_refs": { "decision:<ci-decision-if-any>": null },
  "acceptance": ["WHEN a pull request is opened THEN CI SHALL run lint + test + build and report a status check"],
  "verify": { "kind": "manual", "handle": "push a branch and confirm the ci workflow goes green" },
  "files": [".github/workflows/ci.yml"]
}
```

## This is the PROJECT's CI — not the template's

Bedrock's own self-test is `tools/run-evals.sh` (run by `.github/workflows/evals.yml`) — a different
file with a different purpose. `ci.yml` is what the seeded project ships for its own code.
