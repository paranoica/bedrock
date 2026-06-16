# .gitignore emitter — genesis composes the project's .gitignore from github/gitignore

genesis writes the seeded project's `.gitignore` by **merging** two halves: **theirs** — the official,
curated patterns from [github/gitignore](https://github.com/github/gitignore) (CC0-1.0) for the
project's stack — and **ours** — bedrock's skill-artifact block. Like the CI emitter, it runs **once**
at project creation (and on `replan` only if the stack changes).

## Selection — by stack (the same signal the CI emitter uses)

Pick fragment(s) from `gitignore-templates/` by the project's **stack** (`AGENTS.md` → "Project rules"
→ Stack). Always include `common`; always append `bedrock` **last**.

| Fragment | When |
|----------|------|
| `common.gitignore`  | ALWAYS — OS, editors, env/secrets, logs, temp |
| `node.gitignore`    | Node / TypeScript |
| `python.gitignore`  | Python |
| `go.gitignore`      | Go |
| `rust.gitignore`    | Rust |
| `bedrock.gitignore` | ALWAYS, LAST — the skill-artifact block ("ours") |
| (none)              | unrecognized stack → `common` + `bedrock` + a `# TODO(genesis): add <stack> patterns` marker — never a fake-complete ignore |

**Monorepo / multi-stack** (e.g. Node front + Python back): append BOTH stack fragments. Order is
always `common` → each stack fragment → `bedrock`.

## Compose — the "наш + ихний" merge

Concatenate the selected fragments **verbatim**, each under its own header comment, in order:
`common` → `<stack>` [→ `<stack2>`] → `bedrock`. Do **not** rewrite or re-order patterns inside a
fragment. De-dupe only **exact-duplicate** lines across fragments (e.g. `dist/` in both node and
python) — keep the first, drop the later duplicate; never silently drop a unique pattern.

## Source fidelity & refresh (the one optional network use)

Fragments are **vendored** (committed here) from github/gitignore at a known state — so genesis works
**offline and deterministically** (same principle as `ci-templates/`). At generation genesis MAY
refresh a fragment from the official source — one call to
`https://raw.githubusercontent.com/github/gitignore/main/<Lang>.gitignore` (e.g. `Python.gitignore`)
plus the relevant `Global/*` — and re-curate it. **Offline → use the vendored fragment as-is and leave
a `# verify against github/gitignore` comment.** Never block on the network.

## Hard rules (teeth)

- **Never ignore a lockfile.** `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`,
  `poetry.lock`, `Cargo.lock` (for an app), `go.sum` are **committed** — a `.gitignore` that hides one
  breaks reproducible installs. (This is the exact bug the template's own `.gitignore` once had.)
- **No trailing comments on a pattern line** — a `# …` after a pattern becomes part of the pattern and
  silently breaks the ignore (the same gotcha the whole repo follows).
- **Don't blanket-ignore `.vscode/`** — `common` ignores `.vscode/*` but keeps the shared
  `settings`/`tasks`/`launch`/`extensions` files (the github/gitignore approach).
- **Never overwrite a user's existing `.gitignore`** — if one is present, read-and-extend: append only
  the missing `common`/`<stack>`/`bedrock` sections, each under its header; never drop their lines.

## This is the PROJECT's .gitignore — not bedrock's own

bedrock's own root `.gitignore` covers only its skill artifacts + its own dev noise; it is **not** the
template a seeded project receives. The composed file above is.
