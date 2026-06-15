---
name: code-review
version: 2.1.1
description: Hard, no-mercy code review — security (especially injections: SQLi, XSS, SSRF, command injection, deserialization, prototype pollution, memory-safety), performance, correctness. Use whenever the user wants code reviewed, audited, or checked for bugs/vulnerabilities — a PR, uncommitted changes, or a whole project — including a bare "what do you think" on shared code and Russian cues like "посмотри мой код", "проверь на баги", "найди уязвимости". Deep coverage JS/TS, Python, SQL, Go, C/C++, C#, Java/Kotlin, PHP, Shell, Rust, plus infra (CI/CD, Docker, Kubernetes, Terraform, Redis, GraphQL, web servers, cloud); any other language via the language-agnostic taint-spine. Pulls fresh CVEs from OSV.dev and current advisories from the web. This skill reviews existing code for correctness/safety; building or redesigning a site's visual layer is design-creator's job, not this one.
---

# Code Review Skill

A senior-engineer-level reviewer that doesn't soften, doesn't pad, and doesn't praise
unless something is genuinely worth praising. Focused on **security** (extra paranoia
around injections and memory-safety), **performance**, and **maintainability**.

## Read this first, every review

1. **`index.json`** — the router + state map. It tells you which files this task needs
   (lazy loading) and where durable state lives. Read it before anything else.
2. **`references/invariants.md`** — the compact non-negotiable core. Re-read it at the
   start, before writing `findings.json`, and at the grounding gate (reinjection — this
   fights context rot in long sessions; the invariants are short so it's cheap).

The full reasoning behind the invariants (anti-hallucination, anti-laziness, fix-safety,
the false-positive catalog) lives in **`references/review-discipline.md`** — pull it at the
grounding gate (Step 5c) and before applying a fix, not for the whole review. The one rule
under all of it: **a finding = a tainted source AND an unsafe sink in the same flow, grounded
in a line you actually read** — never an assumed pattern, a fabricated CVE/line, or a real bug
rationalized away.

## Routing — pick a mode

Read the user's request and pick ONE mode (file paths in `index.json` → `mode_routes`).
If unclear, ask.

| User says... | Mode |
|---|---|
| "review my project", "audit the whole codebase", "посмотри весь проект" | **full-project** |
| "review my changes", "проверь что я наклепал", "check uncommitted", git diff/staged/unstaged | **uncommitted** |
| "review PR #123", "проверь чужой PR", a GitHub PR URL | **pr-review** |

Read the mode's file in `modes/` for its workflow, then continue here.

## Universal workflow (after mode-specific setup)

Once the mode has produced **a set of files/diff to review**, do this.

### Step 0 — Preflight (environment capability, run ONCE)
Run `scripts/preflight.sh` (`--no-net` offline). It probes the static-analysis toolchain
(semgrep/gitleaks/bandit/eslint), `python3`/`node`, OSV reachability, **and the PoC-execution
isolation backend** (Step 5d), returning a JSON capability report with a derived `mode`
(`full` | `degraded`) and `install_hints`.

**Announce the operating mode in one line, up front.** `mode: full` → proceed silently.
`mode: degraded` → e.g. "Degraded: no semgrep/bandit, OSV unreachable, no PoC isolation →
LLM review + deterministic verifier; dep-CVE scan and execution-grounding skipped, those
findings flagged lower-confidence." Then continue — **never abort.** This is the contract
that makes every later "skipped" honest. Carry the report in working memory.

### Step 0b — Load learned context (suppressions + standards)
If `.review/` exists (paths in `index.json` → `state_files`): load `suppressions.json`
(prior FP signatures → default-suppress unless you have *new evidence* of a real unsafe
path; test with `scripts/record_outcome.py match …`) and `standards.md` (accepted repo
conventions — a change violating one is itself a finding). First run has neither; they get
built at close-out (Step 6). This is how the reviewer stops crying wolf on the same pattern.

### Step 1 — Detect stack + infra + versions
From lockfiles and entry points, record which **languages**, **SQL/data stores**, and
**infra/tooling** are in play (`package.json`/lockfiles → Node/JS/TS; `requirements`/
`pyproject`/`poetry`/`Pipfile` → Python; `go.mod` → Go; `*.csproj`/`*.sln` → C#;
`pom.xml`/`build.gradle` → Java/Kotlin; `composer.json` → PHP; `Cargo.toml` → Rust;
`Makefile`/`CMakeLists`/`*.c`/`*.cpp` → C/C++; `*.sh` → Shell; `Dockerfile`,
`.github/workflows`, `*.tf`, `k8s`/`helm` manifests, `nginx.conf`, etc. → infra). These
select the modules in Step 5 via `index.json` → `stack_routes` / `infra_routes`.

**Record versions, not just stacks.** Pull the runtime + key framework majors from the
lockfile. Footguns are version-specific — don't flag what the project's version already
fixed; do flag what exists in *their* version. State the version and how you confirmed it.

### Step 1b — Diff-mode extras (uncommitted / pr-review only)
- **Score the change:** `scripts/change_risk.py --git <base_ref> .` → 0–100 risk, per-file
  ranking, flags `too_big` / `mixed_concerns` / `risky_no_tests`. Surface up front; use the
  ranking to decide where to read deepest.
- **Review the deletions:** read `checklists/removed-defenses.md`, walk the diff's `-` lines.
  A removed auth check / validation / timeout / transaction / test is a finding at the
  severity of what it protected — unless you confirm it moved and still covers the path.

### Step 1c — Build the repo map (cross-module memory)
Run `scripts/build_index.py <repo_root>` once → persistent `.review/index.json` mapping
files to symbols they **define** and names they **call**, plus reverse edges. Use it before
calling a change "local": `--callers <symbol>` (blast radius includes callers outside the
diff — go read them) and `--defs <symbol>` (resolve a sink's real definition instead of
assuming). It's a coarse map — treat edges as *leads to read*, never findings on their own.
Absent/stale → say "repo map unavailable, cross-module reasoning limited to files read".

### Step 2 — Run the tooling layer
Run `scripts/run_static_analysis.sh <target> [files_list]` (pass the changed-files list in
diff modes so tool output lines up with the diff). Wraps semgrep, gitleaks, bandit, eslint.
Missing tools land in `tools_skipped` — tell the user once + surface the matching preflight
install hint, then continue. **Capture the JSON; don't dump it.** It's input for Step 5:
cross-reference, drop noise, keep signal.

### Step 3 — Check CVEs via OSV.dev
Run `scripts/check_cves.sh`. Parses lockfiles (npm/pnpm/yarn classic+berry; poetry/Pipfile/
requirements), batch-queries OSV, computes severity from the CVSS vector, carries `fixed`
versions. If `deps_total > deps_scanned`, say the cap was hit. A lockfile parsing to zero
deps is a **tooling gap to report, not "no vulnerabilities".** Vulnerable deps go at the top
as CRITICAL (or computed band). **If OSV is unreachable the scan is SKIPPED, not clean** —
state it, escalate the Step 4 web budget to the few highest-risk deps, mark those
lower-confidence.

### Step 4 — Web-augment for fresh threats
Targeted searches **only if local data isn't enough**: new CVE classes for the framework,
specific pattern uncertainty, a dependency at an unusual version. **Budget: max 5 searches.**
Cache topic+date so you don't repeat.

### Step 5 — LLM-driven review
First read **`checklists/taint-spine.md`** — the language-agnostic source→sink→sanitizer
model and the finding rule. Then load checklists by relevance via `index.json` (don't read
all of them — that just burns context):
- `always_checklists` — injection-deep, security-general, performance, resilience. Every review.
- `stack_routes` — the language module(s) for the detected stack(s) only.
- `infra_routes` — the misconfig checklist(s) for detected infra only.
- `conditional_checklists` — concurrency / migrations / removed-defenses / privacy / finops /
  architecture / test-quality / supply-chain / llm-slop, each loaded only when the diff
  actually triggers it.

Then walk the files/diff with the checklists open. For each file: skim for entry points;
**build a taint map** (every public input → trace through the call graph to every sink:
DB query, shell, file, outbound HTTP, template render, response body, eval-like construct;
when a flow crosses a file boundary resolve the callee with `build_index.py --defs` and its
blast radius with `--callers`); for each tainted flow check the matching injection rule;
**verify defenses by reading them** (construct the input that *would* exploit, check the
defense stops it); check perf on loops/queries; cross-reference tool findings and drop FPs.
**A finding requires a tainted source AND an unsafe sink in the same flow.** The full
false-positive catalog is in `references/review-discipline.md`.

### Step 5b — Improvements pass (MANDATORY, even at zero bugs)
A separate pass. Read `checklists/improvements.md` fully (strict rules on what qualifies).
Hard cap **5–7 improvements**, categorized by IMPACT (not severity). Nothing worth saying →
exactly one line in the user's language ("Code clean — nothing substantial to suggest." /
"Код чистый — ничего существенного не предложу."). Don't pad.

### Step 5c — Ground every finding before it ships (MANDATORY)
Re-read `references/invariants.md` and `references/review-discipline.md` (the verification
section). Then:
1. Write findings to `findings.json`: `{"findings":[{"id","severity","category","confidence",
   "file","lines":[s,e],"quote":"<verbatim code>","cve":null}, …]}`.
2. Run `python3 scripts/verify_findings.py findings.json <repo_root> <osv_output.json>`. It
   writes a hash-bound `.review/verify-receipt.json` (binds findings + the sha256 of every
   source file it read + the verdict counts). Put its `receipt_id` on the report's Verification
   line as `receipt:<12-hex>` — this is what makes the counts un-forgeable.
3. Honor verdicts: `CUT_NO_FILE`/`CUT_NO_QUOTE`/`CUT_BAD_CVE` → delete; `RELOCATE` → keep,
   replace lines with `actual_lines`; `NEEDS_HUMAN` → keep only as `needs verification`;
   `VERIFIED` → ship. When it says CUT, you cut — don't rephrase it back in.
4. **Self-consistency** for `confidence: low` survivors: re-derive once from scratch; can't
   reproduce → downgrade or cut.
4b. **Counterfactual on "safe" verdicts:** when you called a spot safe *because of a defense*,
   construct the specific exploit input and trace whether the defense stops it. If something
   slips through, it's a finding after all.
5. **Spawn the verifier subagent** for medium+ reviews (≥5 findings or any CRITICAL/HIGH):
   `Task(subagent_type:"general-purpose", prompt: <contents of subagents/finding-verifier.md>
   + the findings JSON + repo root + OSV output path)`. Fresh context → can't be anchored by
   your reasoning. Treat its cut/downgrade as authoritative unless you can point at the exact
   refuting line. Gate by scope. Fallbacks: a user-registered `finding-verifier` agent by
   name; else the deterministic verifier + self-consistency still cover grounding.

### Step 5d — Execution-grounding (when safe; strongest receipt)
For a CRITICAL/HIGH security finding whose exploitability reproduces in a few lines, an
executed PoC beats reasoning. Gate on ALL: preflight `poc_execution.available: true`; the
hypothesis is reproducible in a **self-contained snippet** (no live app/DB/network). Write
the minimal PoC with a success marker, run `scripts/poc_runner.sh --lang py|js --code '<poc>'
--expect VULN_CONFIRMED` (isolated, no network, resource-limited, repo not writable).
`confirmed: true` → cite "Execution: reproduced". `confirmed: false` → **does NOT prove
safety** (likely the PoC was wrong); keep at reasoned severity or downgrade only if the
reasoning was shaky. `available: false` → leave the finding as reasoned. The runner executes
**only your tiny PoC** — never the project's app/tests/build/install, never a fix.

### Step 6 — Write the report + close out
Output format is fixed: read `references/report-template.md` and follow it. **Adapt detail
to scope** (tiny diff → conversational enumerate; PR → full template tight; big audit →
group by file, count table at top). Order: vulnerable deps → CRITICAL → HIGH → MEDIUM → LOW
→ Improvements → Summary (2–3 lines, brutally honest). Never split related issues to inflate
the count. No emojis, no padding, no "I hope this helps."

**Self-check the report before shipping it.** Run `python3 scripts/check_report.py <report.md>
--receipt .review/verify-receipt.json --repo <repo_root>` (or pipe the rendered report on stdin
with `-`). It deterministically fails if the mandatory receipts are missing — the **Verification**
line with its tier, the literal `verify_findings.py` counts (VERIFIED/RELOCATE/CUT/NEEDS_HUMAN),
**and its hash-bound `receipt:<12-hex>` id** — the Coverage & limits block, the Scope/Stack/Tools
lines, or if an emoji slipped in. With `--receipt` it goes further: it recomputes the receipt id,
re-hashes the cited source files **from disk**, and confirms the counts equal the receipt — so a
hand-typed Verification line cannot pass without `verify_findings.py` having actually run against
the real files. A non-zero exit means the grounding gate (Step 5c) left no honest receipt: fix the
report, don't ship around it. This turns the
"mandatory" sections from prose you can quietly skip into an omission that is *visible*.

**Close-out (learning loop).** When findings get resolved, log outcomes with
`scripts/record_outcome.py {tp|fp} …` — feeds the Brier scorecard, records FP signatures into
`.review/suppressions.json` and accepted conventions into `.review/standards.md`, so the next
review on this repo is smarter. Commit those two; `.review/index.json` and `outcomes.jsonl`
are rebuildable/local. **Tune for precision first, per category** (raw SQL / auth / crypto
can run hotter than style/perf nits); when you have a labeled set, score with `evals/score.py`
and read **F1**, not catch-rate.

Confidence maps to a true-positive probability (high≈0.9, medium≈0.65, needs-verification≈0.35;
`scripts/calibration.py p <label>`). Check `scripts/calibration.py report` — the Brier score
tells you whether "high confidence" actually means it, so labels stay honest over time.

## Cross-skill: working with design-creator

Cooperate without looping (see design-creator's `tools/handoff.md`).

**Activation boundary (who answers a bare "what do you think" on a web page).** This skill owns
*"is it correct/safe?"* — bugs, security, perf, on **existing** code. design-creator owns
*"build/redesign the visual layer."* When the user shares frontend code and the intent is
ambiguous, this skill takes it: a review is read-only and non-destructive, and it *offers* the
design handoff if findings turn out design-dominated. A request to **design/redesign/build** a
UI is design-creator's, not a review. This deterministic split is what stops both skills matching
the same message.

**Spawned BY design-creator** (prompt contains `HANDOFF=design-creator`, review-only): review
the listed files only; focus on fatal/security bugs, frontend-safety, accessibility, CWV/
bundle/render perf, supply-chain on added deps. **Return findings only — do not auto-fix, do
not hand off onward** (you are the leaf, depth=1).

**Run normally, hitting design/frontend issues:** if findings are dominated by design/a11y/UX,
**suggest** — never auto-launch — handing them to the design engine with a scoped prompt. Wait
for the user's yes. Suggest-only is what keeps the two from ping-ponging.

## When to STOP and ask

- Project >500 source files with full-project requested → say it'll take many passes, ask to
  scope (most-risky module first, or changes since tag X).
- A file has clear malicious intent (backdoor, exfil) → stop, flag loudly, ask if known.
- Empty diff / nonexistent PR → say so, don't fabricate.

## What this skill does NOT do

- **Does not auto-fix.** It reports; the user can ask "apply the fix for #3" separately.
- **Does not run the project's app/tests/build/install.** Static by default. The one guarded
  exception is Step 5d: a minimal self-contained PoC snippet it wrote, under isolation, only
  when preflight reports a backend. No isolation ⇒ no execution. `scripts/` are read-only
  analyzers; `poc_runner.sh` is the one sandboxed executor and runs nothing from the project.
- **Does not approve or merge.** Output is a report.
