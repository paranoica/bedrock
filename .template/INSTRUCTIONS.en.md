# Bedrock — instructions (EN)

Everything the template does, how each part works, and the edge cases. For the short pitch read
[OVERVIEW.en.md](OVERVIEW.en.md) first.

---

## 0. The flow

1. **Use this template** on GitHub → clone → open in Claude Code.
2. Say what you want to build, or run `/genesis`.
3. genesis interviews you and writes your spec + plan + rules + a first map, and **replaces the
   stub `README.md`** with your project's own.
4. From then on, each change runs through the right gate (below). You talk; the files stay in sync.

---

## 1. genesis — inception & (re)planning

The front door. Owns "start/plan a project". It does **not** review code (that's code-review) or
design UI (that's design-creator).

### Modes
- **greenfield** — empty repo, new project → full pipeline.
- **adopt** — an existing repo that has no spec/rules → genesis reverse-engineers a skeletal spec,
  rules, and map **without reviewing the code**.
- **replan** — the spec changed, **or new work is requested** (e.g. routed from prompt-refiner) →
  re-derive the backlog.

### The interview
Depth scales to complexity (a tiny task → a couple of questions; a multi-surface product → deep). It
asks **one open question at a time** (discrete forks may be grouped within one topic), and **never
invents a decision you didn't make** — unknowns become `TODO(decision: …)` in `docs/open-questions.md`.
Say "just do what's best" and it proceeds on sensible defaults but still extracts the minimum.

### What it produces (your source of truth)
- `docs/decisions.md` · `architecture.md` · `glossary.md` · `open-questions.md` — the spec.
- `PLAN.md` (human) + `genesis.tasks.json` (machine) — the task plan.
- `RULES.md` + `CLAUDE.md` — the rules every coding session follows.
- `README.md` — your project's readme (replaces the Bedrock stub).
- `.map/project.json` — a first structural map.
- `project-context/` — the raw interview + a summary (history, **not** the source of truth).

### How re-planning stays honest (the anchor mechanism — basic + edge)
Each atomic spec unit (a decision, a glossary term, an architecture invariant) carries a stable
**anchor**; each task records which anchors it was derived from (`spec_refs`) with a content **hash**.

- **Basic:** edit a decision's wording → the tasks tracing it become `needs-review` (a soft "confirm
  this still holds"). Re-derive with the backlog tool; `done` work is preserved.
- **Edge — formatting vs meaning:** a pure formatting change (bold a word, re-wrap a line) does **not**
  flag anything — the hash ignores formatting. Only a real wording change flags.
- **Edge — structural vs content:** renaming/removing an anchor a task depends on → that task goes
  `stale` (it must be re-derived), not just `needs-review`. A `done` task whose anchor is removed
  becomes `needs-review`, never silently un-done.
- **Edge — transitive:** change a glossary term and every task that depends on it *through* a decision
  is flagged, even with no direct task→term link.
- **Edge — open decisions block work:** a task that depends on an unresolved `TODO(decision: …)` is
  flagged "not execution-ready" by the gate — the unknown physically blocks the dependent work instead
  of being a loose note.

### The gate before "ready" (spec-analyze)
Two layers: a deterministic check (every requirement traces to a task and back; no contradictions in
anchoring; no dangling refs) **plus** a fresh-context "spec-verifier" that reads the spec cold and
looks for coverage gaps, contradictions, and invented decisions. The gate is blocking.

### adopt-mode honesty (edge)
In adopt mode genesis can see **what** the code is but not **why**. Observed facts go to
`architecture.md` **with file:line citations**; reverse-inferred rationale goes to `open-questions.md`
as `inferred/unconfirmed` — it is **never** asserted as a settled decision until you confirm it.

---

## 2. prompt-refiner — the residue catcher

Catches vague requests **only when no other skill owns them**, and turns them into a precise prompt.

### When it fires vs stays silent (the residue test)
The test is **"can a profile engine start as-is?"**, not the topic:
- Resolves to one engine (even if vague *inside* it — that engine will ask its own question) → routes
  there, **stays silent**. ("make the button nicer" → design-creator.)
- Doesn't resolve — doubles between engines or has no target ("do something about onboarding, it's
  bad") → **residue → refiner takes it**, sharpens, routes.
- **Edge — managed project:** a feature request ("add a reviews section") in a genesis-managed repo
  (has `docs/` + `genesis.tasks.json`) routes to **genesis replan** (it enters the spec + backlog),
  *not* straight to code. In a non-managed repo, refiner sharpens it directly.
- **Edge — doubt:** if it's borderline whether an engine could start, refiner **yields** (stays
  silent). A wrong silence is cheap (the engine asks); a wrong grab is an annoying extra round.

### What it does when it takes
Discovers the target via tools (rather than asking), then writes a precise prompt — one task, explicit
files, acceptance criteria, a verification handle, a reference pattern — and routes it. It asks **at
most one** clarifying question, only when interpretations diverge into materially different work. It
sharpens silently and is **cancelable in one word**.

---

## 3. project-map — the shared code map

`tools/project-map/build.py` walks the repo and emits `.map/project.json`: files → symbols they
define/call (+ reverse edges), and best-effort **domain slices** (routes, data-model, FSM, queues).

- **Freshness (the point):** the map carries a stamp. Before relying on it, run
  `build.py <root> --check` → `fresh` / `stale` / `absent` (exit 0/1/2). `stale` → rebuild
  incrementally (`build.py <root>`). **A stale map is never served as fact.**
- **Edge — leads, not facts:** every map edge and slice item cites `file:line` and a confidence; open
  it and confirm before relying. A weakly-detected slice is marked `low` confidence, not dropped;
  `absent` means "no lead found", not "nothing exists".
- **Edge — unknown stack / non-git:** an unrecognized framework yields no false slice (absent);
  without git, freshness falls back to a content hash of the files (still works).

---

## 4. design-creator & code-review (vendored engines)

- **design-creator** designs/builds web UI. genesis hands it a **structured brief**
  (`.genesis/design-brief.json`: domain, audience, surfaces, scope, tone, brand assets) — **no hook or
  narrative** (that would collapse its output diversity). The brief is consumed by the agent invoking
  design-creator (fed into its survey), not by an autonomous file reader.
- **code-review** audits existing code. The mandate is a loop: **implement → review → apply fixes →
  re-review**, scaled to risk (trivial diff → light; auth/money/migrations → full).

---

## 5. The canon & the file-driven loop

`RULES.md` is the single rule source; `CLAUDE.md` is a thin wrapper that imports it. It encodes the
**gate mandates** (design→design-creator; audit→code-review loop; everything else→the loop below) and
the **map-read protocol**. The residual-work loop:

1. `backlog.py next` → the next ready task.
2. Do one task (stay in its `files`, satisfy its `acceptance`).
3. Run the matching gate, scaled to risk.
4. `backlog.py done <id>`.
5. Re-read the invariants at the boundary, then loop.

**Edge — never hand-edit the plan:** task state changes only via `backlog.py`. `PLAN.md` is generated;
if you (or anything) hand-edit `PLAN.md` or `genesis.tasks.json`, `backlog.py validate` re-renders and
diffs, so the desync **fails visibly** (it can't drift silently).

---

## 6. Tooling & self-checks (for working on the template itself)

- `tools/project-map/build.py` — the map (above).
- `.claude/skills/genesis/scripts/backlog.py` — the backlog tool (`stamp`/`next`/`done`/`status`/
  `re-derive`/`validate`/`render`).
- `tools/contract.json` — the **single source** of cross-skill paths, commands, and anchor facts.
- `tools/drift-check.py` — fails if the canon, the map contract, and genesis's scripts ever **disagree**
  on those (not just if a file is missing). Four linkages: map-path, gate-commands, anchor-facts,
  design-brief.
- `tools/run-evals.sh` — one command that runs **every** regression (drift-check + the genesis seam
  test + a map smoke) and fails if **any** fails. CI (`.github/workflows/evals.yml`) runs the same.

```bash
bash tools/run-evals.sh
```

---

## 7. What's committed vs rebuilt (don't break this)

- **Committed** (source of truth + history): `docs/`, `PLAN.md`, `genesis.tasks.json`, `RULES.md`,
  `CLAUDE.md`, `README.md`, `project-context/`, plus each vendored skill's learned state
  (`.design/tokens.json`, `.review/suppressions.json`, …).
- **Git-ignored** (rebuildable / local): `.map/`, `.genesis/`, `.refiner/`, `.design/mockups/`,
  `.review/index.json`, `.review/outcomes.jsonl`.
- **Edge — why it matters:** a committed stale `.map/` would lie to the next clone; a git-ignored
  `genesis.tasks.json` would lose the backlog. The split is load-bearing.
- **Edge — `.gitignore` gotcha:** patterns there have **no trailing comments** (a `# …` on a pattern
  line becomes part of the pattern and silently breaks the ignore). Comments live on their own lines.

---

## 8. Evolution gotcha (for maintainers)

The anchor hash is computed by one function (`scripts/anchors.py: normalize()`), shared by the
generator and the gate. **Changing `normalize()` re-hashes every anchor in every project that used
this template** — it is a *breaking migration*, not a fix. Version it deliberately; never patch it
quietly.
