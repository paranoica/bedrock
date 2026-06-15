# Project Map — contract

The **project map** is a persistent, skill-agnostic structural map of a repository. Any skill
(`genesis`, `code-review`, …) reads the map instead of re-deriving the project from scratch on
every task. This file is the shared handoff surface — the analogue of `design-creator`'s
`.design/tokens.json`. It documents **where the map lives, its schema, how freshness is stamped,
and the read protocol every consumer must follow.**

Built by `tools/project-map/build.py` (stdlib Python 3, generalized from
`code-review/scripts/build_index.py`).

## The one rule

> **Map edges and slice items are LEADS TO READ, not facts on their own. A stale map is never
> served as fact.**

Everything below exists to keep that rule enforceable, not aspirational.

## Where it lives

```
.map/project.json        the map (single JSON file)
```

`.map/` is **rebuildable and gitignored** — it is derived state, never the source of truth (the
source of truth is the code itself). Do not commit it; rebuild it.

## Schema (`.map/project.json`)

```jsonc
{
  "version": 1,
  "root": "/abs/path/to/repo",

  "stamp": {                         // FRESHNESS — see "Freshness" below
    "git_head": "9f3c…" | null,      // HEAD sha if a git work tree, else null (diagnostic)
    "git_dirty": true | false | null,// uncommitted changes present? (diagnostic)
    "tree_hash": "a1b2c3d4e5f6a7b8", // AUTHORITATIVE staleness signal (see below)
    "file_count": 412
  },

  "files": {                         // one record per mapped source file
    "apps/api/auth.py": {
      "hash": "…",                   // sha256[:16] of file bytes (incremental reuse key)
      "lang": "py",                  // or "py-parse-error" if Python failed to parse
      "defs":  ["login", "verify_token", "AuthError"],   // functions/classes/methods defined
      "calls": ["execute", "decode", "get"],             // names called (leads, not a call graph)
      "slices": { "routes": [ … ] }  // per-file slice hits (aggregated up into top-level "slices")
    }
  },

  "symbols": { "verify_token": ["apps/api/auth.py"] },   // reverse: name → files that DEFINE it
  "callers": { "verify_token": ["apps/api/views.py"] },  // reverse: name → files that CALL it

  "slices": {                        // DOMAIN SLICES — best-effort, see "Slices" below
    "routes": {
      "confidence": "high" | "low",
      "count": 23,
      "discipline": "leads to read, not facts — open file:line and confirm before relying",
      "items": [
        { "method": "POST", "path": "/login", "file": "apps/api/auth.py",
          "line": 88, "evidence": "@router.post(\"/login\")", "confidence": "high" }
      ]
    },
    "data_model": { … }, "fsm": { … }, "queues": { … }
  }
}
```

Notes:
- `defs`/`calls` are a coarse symbol map (Python via `ast`; other languages via regex). `callers`
  answers "who calls X?" and `symbols` answers "where is X defined?". **Both are leads** — an edge
  means *go read that file*, not *this is a confirmed caller*.
- Output is written compactly with sorted keys (stable diffs) via an **atomic** temp-file rename,
  so a concurrent reader never sees a half-written map.

## Freshness (the hard part — first-class, not a bolt-on)

`tree_hash` is the **authoritative** staleness signal: `sha256` over the sorted
`(relative_path, file_hash)` pairs of every mapped file. It changes if and only if any mapped
file's content changes, or a file is added/removed — **whether or not the change is committed**.
`git_head`/`git_dirty` are diagnostics only; they are not used for the staleness decision (so the
map works the same in a non-git repo).

Probe freshness with `--check`. It re-hashes every mapped file's bytes but does **not** re-parse
them — so it is **cheaper than a build, not free**: the cost is O(repo bytes) of I/O. Call it once
before an analysis pass, not in a hot loop:

```
python3 tools/project-map/build.py <root> --check
```

States and exit codes:

| State    | Exit | Meaning |
|----------|------|---------|
| `fresh`  | 0    | `tree_hash` matches the map — safe to consult. |
| `stale`  | 1    | files changed since the stamp — `changed_files`/`removed_files` listed; rebuild. |
| `absent` | 2    | no map (or unreadable / wrong schema version) — build first. |

A `stale` result lists the changed files so a rebuild is incremental: `build.py` reuses every
file whose `hash` is unchanged and re-parses only the rest, then refreshes the stamp.

## Read protocol (every consumer follows this; canon `AGENTS.md` re-states it)

1. **Before analyzing the project, run `--check`.**
2. `fresh` → consult the map.
3. `stale` → **incrementally rebuild** (`build.py <root>`), then consult. Only changed files are
   re-parsed; the stamp is updated.
4. `absent` and you can build → build, then consult.
5. `absent`/`stale` and you **cannot** rebuild (no Python, read-only FS, etc.) → say so and fall
   back to **"analysis limited to files I actually read"**. **Never serve a stale map as fact.**
6. Treat every edge and every slice item as a **lead to read**: open the cited `file:line`,
   confirm, and only then rely on it.

## Slices — `routes` / `data_model` / `fsm` / `queues`

Slices are **best-effort, framework-pattern detection**. They surface where to look; they do not
assert truth.

- Every item carries `file` + `line` + `evidence` (the matched snippet) so a consumer can verify
  in one jump, plus a per-item `confidence`.
- **`confidence: "high"`** = a recognized framework marker matched (e.g. `@router.post(...)`,
  Prisma `model X {`, `new Queue("…")`, `createMachine(`). **`confidence: "low"`** = a heuristic
  shape worth reading but easily a false positive (e.g. Next.js file-based route by path, Pydantic
  class as a possible data model, RQ `.enqueue(`).
- A slice's top-level `confidence` is `"high"` if any item is high, else `"low"`.
- **Low-confidence is shown, not dropped.** A weakly-detected lead is more useful than silence and
  is still honest (it is labelled). **Absent** means "no lead was found", which is *not* a claim
  that nothing exists — only deeper reading proves absence.
- Detection is conservative by design (under-report rather than fabricate). What is covered today:
  - **routes** — FastAPI/Flask/APIRouter decorators, Django `urls.py` `path()`, Express/Fastify
    `app|router.<verb>(...)`, Next.js file-based routes (low).
  - **data_model** — SQLAlchemy/Django/SQLModel ORM classes, Prisma `model`, TypeORM `@Entity`,
    Mongoose `Schema`, Pydantic (low).
  - **fsm** — explicit state-machine libraries only (`python-statemachine`/`transitions`, XState).
    Bare `*Status` enums are intentionally **not** detected — too noisy to be an honest lead.
  - **queues** — Celery tasks, BullMQ `Queue`/`Worker`, NestJS `@Processor`/`@Process`, RQ (low).
  - Unknown stacks fall through to absent on the slice (no fabricated leads).

## Commands

```
build.py <root>                       # build (incremental by default; reuses unchanged files)
build.py <root> --force               # full rebuild, ignore cache
build.py <root> --check               # freshness probe (JSON; exit 0/1/2)
build.py <root> --callers <symbol>    # reverse edge: files that call it
build.py <root> --defs <symbol>       # forward edge: files that define it
build.py <root> --slice routes        # dump one domain slice
```

## What this is NOT

- **Not a semantic / concept graph.** Structural only: files, symbols, dependencies, data model,
  routes, FSM, queues. No Obsidian-style concept linking (low ROI, near-impossible to keep true).
- **Not a call graph.** `calls`/`callers` are name-level leads, not resolved call edges.
- **Not authoritative.** The code is the truth; the map is a fast, freshness-stamped index over it.
