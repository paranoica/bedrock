# Bedrock — instructions (EN)

Everything the template does, how each part works, **how to use it correctly**, and a full catalog of
edge cases. For the short pitch read [OVERVIEW.en.md](OVERVIEW.en.md) first.

---

## 0. The flow

1. **Use this template** on GitHub → clone → open in your coding agent.
2. Say what you want to build, or run `/genesis`.
3. genesis interviews you and writes your spec + plan + rules + a first map, and **replaces the stub
   `README.md`** with your project's own.
4. From then on, each change runs through the right gate. You talk; the files stay in sync.

---

## 1. How to use it correctly (do / don't)

**Do**
- **Run genesis first** on a new or unplanned project — before writing code. It is the front door.
- **Answer the interview honestly, including "I don't know."** "Don't know" is a feature: it becomes a
  recorded open question, not a guess.
- **Read `docs/` and `PLAN.md`** once genesis is done — that's your spec and plan; confirm they match
  your intent before building.
- **Build through the loop:** `backlog.py next` → do one task → run the matching gate → `backlog.py
  done <id>`. One task at a time.
- **Change the spec, then re-derive.** Edit `docs/` (or add a feature via `replan`), then
  `backlog.py re-derive` — let the plan re-split. Don't hand-patch the plan.
- **Scale the gate to risk:** trivial diff → light review; auth/money/migrations/crypto → full
  code-review.
- **Run `bash tools/run-evals.sh`** before changing the template's own tooling or skills.

**Don't**
- **Don't hand-edit `PLAN.md` or `genesis.tasks.json`** — change state only via `backlog.py` (a
  hand-edit fails `validate` visibly).
- **Don't rewrite `AGENTS.md`'s universal section** — your project's rules go in its "Project rules"
  section (inline), which genesis fills.
- **Don't feed design-creator a hook/narrative** — give it structured constraints; it forms its own.
- **Don't trust a stale map.** Run `build.py --check` first; rebuild if stale.
- **Don't let a feature land in code around the backlog** in a genesis-managed project — route it
  through `replan` so the spec and plan stay the source of truth.

---

## 2. genesis — inception & (re)planning

The front door. Owns "start/plan a project". It does **not** review code (that's code-review) or design
UI (that's design-creator).

### Modes
- **greenfield** — empty repo, new project → full pipeline.
- **adopt** — an existing repo with no spec/rules → genesis reverse-engineers a skeletal spec, rules,
  and map **without reviewing the code**.
- **replan** — the spec changed, **or new work is requested** (e.g. routed from prompt-refiner) →
  re-derive the backlog. For new work, replan **amends the spec first** (a targeted interview on just
  the delta → anchors it), then re-derives.

### The interview
Depth scales to complexity (a tiny task → a couple of questions; a multi-surface product → deep). It
asks **one open question at a time** (discrete forks may be grouped within one topic), and **never
invents a decision you didn't make** — unknowns become `TODO(decision: …)` in `docs/open-questions.md`.
Early on it pins the **project-type** (web-app / service / CLI / library / worker) — this decides
whether a design-brief is emitted (visual-web only) and how the CI steps are tuned. Late in the
interview it asks **one grouped question — which coding agents your team uses** (to emit the right
wrappers; default = Claude + `AGENTS.md`). Say "just do what's best" and it proceeds on sensible
defaults but still extracts the minimum.

### What it produces (your source of truth)
- `docs/decisions.md` · `architecture.md` · `glossary.md` · `open-questions.md` — the spec.
- `PLAN.md` (human) + `genesis.tasks.json` (machine) — the task plan.
- `AGENTS.md` — the rules every agent follows; genesis fills its **"Project rules"** section inline.
  Plus per-agent wrappers (`CLAUDE.md` = `@AGENTS.md`; others for the agents you selected).
- `README.md` — your project's readme (replaces the Bedrock stub).
- `.map/project.json` — a first structural map.
- `.github/workflows/ci.yml` + `spec-gate.yml` — a real, working CI (see **CI** below).
- `.gitignore` — composed from github/gitignore (your stack) + bedrock's skill-artifact block.
- `project-context/` — the raw interview + a summary (history, **not** the source of truth).

### How re-planning stays honest (the anchor mechanism)
Each atomic spec unit (a decision, a glossary term, an architecture invariant) carries a stable
**anchor**; each task records which anchors it was derived from (`spec_refs`) with a content **hash**.
On a spec change, `backlog.py re-derive` compares hashes and flags tasks — see the edge-case catalog
(§10) for the exact `needs-review` vs `stale` behaviour. `done` work is preserved.

### The gate before "ready" (spec-analyze)
Two layers: a **deterministic** check (each task traces to a real spec anchor — a dangling ref is
CRITICAL; an orphan decision with no task is a LOW flag; no anchoring contradictions; partial
annotation / duplicate ids fail) **plus** a fresh-context **spec-verifier** that reads the spec cold
and judges the harder *coverage* question — is anything required missing a task? — that the
deterministic pass can't prove. The gate is blocking — genesis never declares the spec "ready" on a
skipped **or stale** gate (the receipt's `--check` must be fresh). The deterministic half + backlog
consistency are **also enforced in the seeded project's CI** (`.github/workflows/spec-gate.yml`, pure
Python, no model) — so "blocking" holds mechanically, not only by the model; the fresh-context
verifier is the authoring-time half.

### CI — genesis writes the project's workflow
genesis emits a **real, working** `.github/workflows/ci.yml` (lint / test / build) chosen by **stack ×
project-type** — Node / Python / Go / Rust, or a `generic` skeleton with a TODO for an unrecognized
stack (**never a fake-green CI**). **No AI runs in CI** — it's plain GitHub jobs on GitHub's runners.
It also adds a "Wire up CI" **backlog task** so making it green is a tracked unit, not an unverified
artifact. The only network use is an optional one-time refresh of version pins at generation; **offline
→ it keeps the prototype's pins and leaves a `# verify pins` comment**. The companion `spec-gate.yml`
(the deterministic gate half, above) runs on every PR. This is the *project's* CI — Bedrock's own
self-test is `tools/run-evals.sh` (§8), a different file.

### .gitignore — composed, not hand-rolled
genesis composes the project's `.gitignore` from the **official [github/gitignore](https://github.com/github/gitignore)**
patterns (CC0): a universal `common` base (OS / editors / `.env*` secrets / logs / temp) + the
fragment(s) for your **stack** (Node / Python / Go / Rust; an unknown stack → `common` + a TODO, never
a fake-complete ignore) + bedrock's own skill-artifact block (`.map/`, `.genesis/`, …), merged in that
order. Fragments are vendored (works offline), with an optional one-time refresh from the source.
**Lockfiles are never ignored** (committed for reproducible installs); `.vscode/` isn't
blanket-ignored; an existing `.gitignore` is extended, never overwritten.

### adopt-mode honesty
In adopt mode genesis can see **what** the code is but not **why**. Observed facts go to
`architecture.md` **with file:line citations**; reverse-inferred rationale goes to `open-questions.md`
as `inferred/unconfirmed` — **never** asserted as a settled decision until you confirm it.

---

## 3. prompt-refiner — the residue catcher

Catches vague requests **only when no other skill owns them**, and turns them into a precise prompt.

- **When it fires vs stays silent (the residue test):** the test is **"can a profile engine start
  as-is?"**, not the topic. Resolves to one engine (even if vague *inside* it — that engine asks its
  own question) → routes there, **silent**. Doesn't resolve (doubles between engines, or no target) →
  **residue → it takes it**, sharpens, routes.
- **What it does when it takes:** discovers the target via tools (rather than asking), writes a precise
  prompt (one task, files, acceptance, a verify handle, a reference pattern), asks **≤1** clarifying
  question only on material divergence, and routes. Sharpens silently; **cancelable in one word**.
- See §10 for the managed-project and default-yield edge cases.

---

## 4. project-map — the shared code map

`tools/project-map/build.py` walks the repo and emits `.map/project.json`: files → symbols they
define/call (+ reverse edges), and best-effort **domain slices** (routes, data-model, FSM, queues).

- **Freshness (the point):** the map carries a stamp. Before relying on it: `build.py <root> --check`
  → `fresh` / `stale` / `absent` (exit 0/1/2). `stale` → rebuild incrementally (`build.py <root>`).
  **A stale map is never served as fact.**
- **Leads, not facts:** every edge and slice item cites `file:line` + a confidence; open it and confirm
  before relying. See §10 for the low-confidence / absent / unknown-stack edges.

---

## 5. design-creator & code-review (vendored engines)

- **design-creator** designs/builds web UI. For a **visual-web project-type** genesis hands it a
  **structured brief** (`.genesis/design-brief.json`: domain, audience, surfaces, scope, tone, brand
  assets) — **no hook or narrative** (that would collapse its output diversity); a CLI / service /
  library / worker project gets no brief. The brief is consumed by the agent invoking design-creator
  (fed into its survey), not by an autonomous file reader.
- **code-review** audits existing code. The mandate is a loop: **implement → review → apply fixes →
  re-review**, scaled to risk.

---

## 6. The canon, the loop, and the wrappers

`AGENTS.md` is the **canonical** rules doc (read natively by most agents). `CLAUDE.md` is a thin
`@AGENTS.md` wrapper for Claude Code. Both encode the **gate mandates** (design→design-creator;
audit→code-review loop; everything else→the loop below), the **status seam**, and the **map-read
protocol**. The residual-work loop:

1. `backlog.py next` → the next ready task.
2. Do one task (stay in its `files`, satisfy its `acceptance`).
3. Run the matching gate, scaled to risk.
4. `backlog.py done <id>`.
5. Re-read the invariants at the boundary, then loop.

Your **project rules** live inline in `AGENTS.md`'s "Project rules" section (genesis writes them there
so every agent sees them — not behind a Claude-only `@import`).

---

## 7. Working across agents (agent-agnostic)

`AGENTS.md` is the cross-agent standard, read **natively** by Cursor, Roo Code, Windsurf, and Codex —
no glue. For the rest, genesis emits a thin wrapper for the agents you selected in the interview:

| Agent | What you need |
|-------|---------------|
| Claude Code | `CLAUDE.md` (`@AGENTS.md`) — ships already |
| Cursor / Roo / Windsurf / Codex | nothing — they read `AGENTS.md` natively |
| Aider | one line in `.aider.conf.yml`: `read: [AGENTS.md]` |
| Continue | a generated `.continue/rules/00-bedrock.md` (from `AGENTS.md`) |
| **Antigravity** | a `.agents/rules/bedrock.md` rule = `@/AGENTS.md` (Always On) — its workspace-rules path; global `~/.gemini/GEMINI.md` is the user's, untouched |

Single source: every wrapper points at / mirrors `AGENTS.md`; rules are never restated in a wrapper.
(Skills note: skills are an open standard — agentskills.io — that Codex also conforms to, but Codex
loads them from `.agents/skills/`, not `.claude/skills/`. So these skills are **partly portable** to
Codex: run `python3 tools/port-skills.py <skill>` — it mirrors the folder into `.agents/skills/` and
strips Claude-only frontmatter (`allowed-tools`, `${CLAUDE_SKILL_DIR}`, `$ARGUMENTS`). Port the
consume-side skills (prompt-refiner, code-review, design-creator) — **not** genesis, which runs in
Claude Code. Verified vs the OpenAI Codex docs.)

---

## 8. Tooling & self-checks (for working on the template itself)

- `tools/project-map/build.py` — the map.
- `.claude/skills/genesis/scripts/backlog.py` — the backlog tool (`stamp`/`next`/`done`/`status`/
  `re-derive`/`validate`/`render`).
- `tools/contract.json` — the **single source** of cross-skill paths, commands, and anchor facts.
- `tools/drift-check.py` — fails if `AGENTS.md`'s machine-contract region, the map contract, and
  genesis's scripts ever **disagree** (not just if a file is missing). Four linkages: map-path,
  gate-commands, anchor-facts, design-brief.
- `tools/port-skills.py` — mirror a skill into `.agents/skills/` for Codex (`<skill>` or `--all`),
  stripping Claude-only frontmatter. The copy is a generated mirror — re-run after editing the source.
- `tools/run-evals.sh` — one command that runs **every** regression and fails if **any** fails. CI
  (`.github/workflows/evals.yml`) runs the same.

```bash
bash tools/run-evals.sh
```

---

## 9. What's committed vs rebuilt (don't break this)

- **Committed** (source of truth + history): `docs/`, `PLAN.md`, `genesis.tasks.json`, `AGENTS.md`,
  `CLAUDE.md` (+ any per-agent wrappers), `README.md`, `.github/workflows/` (the emitted CI),
  `project-context/`, plus each vendored skill's learned state (`.design/tokens.json`,
  `.review/suppressions.json`, …).
- **Git-ignored** (rebuildable / local): `.map/`, `.genesis/`, `.refiner/`, `.design/mockups/`,
  `.review/index.json`, `.review/outcomes.jsonl`.

---

## 10. Edge cases & gotchas — the full catalog

**Interview**
- *You can't answer a question* → it's logged as `TODO(decision: …)` in `open-questions.md`; genesis
  does not guess. Resolve it later (it graduates to `decisions.md` keeping its id).
- *You say "just do what's best"* → sensible defaults, but the minimum (scope, core entities, money
  custody if money is involved) is still extracted — it never works on zero input.

**Spec change → re-derive** (`backlog.py re-derive`)
- *Formatting-only edit* (bold a word, re-wrap) → **no drift**. The hash ignores formatting.
- *Wording change to a decision* → tasks tracing it → **`needs-review`** (soft: confirm still valid).
- *Rename/remove an anchor a task depends on* → that task → **`stale`** (must be re-derived).
- *A `done` task is affected* → **`needs-review`**, never silently un-done.
- *Change a glossary term* → every task depending on it *through* a decision is flagged
  (**transitive**), even with no direct task→term link.
- *A task depends on an unresolved `TODO(decision: …)`* → the gate flags it **not execution-ready**
  until the decision is made — the unknown blocks the dependent work.

**The plan / status seam**
- *You hand-edit `PLAN.md` or `genesis.tasks.json`* → `backlog.py validate` re-renders from the source
  and diffs; the desync is a **visible non-zero failure**, not silent drift. Fix: `backlog.py render`
  (and make state changes via `backlog.py`, not by hand).
- *A task's deps aren't done* → `backlog.py done <id>` refuses (deps must be done first).

**The map**
- *`--check` says `stale`* → rebuild (`build.py <root>`); only changed files are re-parsed.
- *`absent` and you can't rebuild* (no Python, read-only FS) → say so and limit analysis to files you
  actually read. Never serve a stale map as fact.
- *A slice is `low` confidence or `absent`* → it's a **lead, not a fact**; open `file:line` and confirm.
  `absent` means "no lead found", not "nothing exists".
- *Unknown stack/framework* → no false slices are invented (the slice is simply absent).

**Skills & routing**
- *A request could be design or code* → routing is deterministic per `AGENTS.md`: design/redesign →
  design-creator; audit existing code → code-review; prompt-refiner fires **only** on residue nothing
  else owns, and **yields on doubt** (a wrong silence is cheap; the engine asks its own question).
- *A feature request in a genesis-managed project* → goes to **genesis replan** (amend spec → backlog),
  not straight to code. In a non-managed repo, prompt-refiner sharpens it directly.
- *You re-run genesis on an existing project* → it **never overwrites** `AGENTS.md`'s universal section,
  a wrapper, or your work — it reads-and-extends and surfaces conflicts.

**Multi-agent**
- *Antigravity* → **supported via `.agents/rules/`**: genesis emits `.agents/rules/bedrock.md` =
  `@/AGENTS.md` (Always On). It does NOT read a root `AGENTS.md` as rules (a corrected earlier claim);
  `~/.gemini/GEMINI.md` is the user's global rules file — genesis doesn't touch it.
- *Codex skills* → **partly portable (verified)**: Codex loads skills from `.agents/skills/`, so run
  `tools/port-skills.py <skill>` to mirror + strip Claude-only frontmatter. Port the consume-side
  skills, not genesis.

**Gate failures (spec-analyze)**
- *Partial annotation* (some atomic units anchored, some not, in a must-anchor file) → **CRITICAL**.
- *Dangling ref* (a `spec_refs`/`refs:` id with no anchor) → **CRITICAL**.
- *Duplicate anchor id* → **CRITICAL**.

**CI (the emitted workflow)**
- *Offline at generation* → genesis keeps the prototype's version pins and leaves a `# verify pins`
  comment; it never blocks on the network.
- *Unrecognized stack* → it emits the `generic.yml` skeleton with a TODO — **never a fake-green CI**
  that passes without running anything.
- *A generated workflow is not a proven one* → `ci.yml`'s real steps only run once there's code, so the
  **first seeded project must show a green Actions run** ("verify on first real seed"). `spec-gate.yml`
  is pure Python and verified locally.

**.gitignore (composed)**
- *Unknown stack* → `common` + bedrock block + a `# TODO(genesis)` marker — never a fake-complete ignore.
- *A lockfile* (`package-lock.json`, `uv.lock`, `Cargo.lock`, …) → **never ignored** — committed for
  reproducible installs.
- *You already have a `.gitignore`* → genesis extends it (appends the missing sections), never overwrites.

---

## 11. Maintainer gotchas

- **`normalize()` is a migration, not a fix.** The anchor hash is one function
  (`scripts/anchors.py: normalize()`), shared by the generator and the gate. Changing it re-hashes
  **every** anchor in **every** project seeded from this template — version it deliberately; never
  patch it quietly.
- **`.gitignore` has no trailing comments.** A `# …` on a pattern line becomes part of the pattern and
  silently breaks the ignore. Comments live on their own lines.
- **Calibration is cold for a long time** (it accrues one project at a time); the flip-cause loop
  **defaults to not charging** the interview bar — "the user changed their mind" is never treated as an
  interview failure.
