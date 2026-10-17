# Review discipline — the full reasoning behind the invariants

`references/invariants.md` is the compact reinjection core. This file is the full text:
the *why* behind each rule and the failure modes it prevents. Pull this at the grounding
gate (Step 5c) and before applying any fix; you don't need it in context the whole review.

## Anti-hallucination protocol

LLM reviewers fail in predictable ways. To avoid them:

- **Never invent CVE numbers or GHSA IDs.** Only cite CVE/GHSA values that came back from
  the OSV.dev script output or that you found via web search in this session. To reference
  a class of vuln, name it ("SQL injection", "prototype pollution") — not a fake CVE.
- **Never invent line numbers.** Before writing `file.ext:42`, re-confirm by reading that
  range. If you can't confirm, write `file.ext:~near function X` instead of fabricating.
- **Never claim a library has a CVE without checking.** "lodash 4.17.20 has CVE-2020-8203"
  is verifiable; "this version of express has a known issue" without specifics is BS — skip it.
- **Never invent package versions.** A referenced "upgrade to vX.Y.Z" must actually exist
  (check the OSV advisory; otherwise say "upgrade to the latest patched version per <link>").
- **Mark uncertain findings explicitly.** Format: `**Confidence:** needs verification —
  <what to check>`. Better to flag 3 high-confidence issues than 10 with half made up.
- **Don't paraphrase code into the "quote".** Quote the actual code verbatim. Paraphrased
  code in a quote is hallucination by another name.
- **If the file is too large to fully read, say so.** Don't pretend to have reviewed code you
  only sampled: "Reviewed first/last N lines; full review requires scoping down."

## Operating discipline — effort, honesty, fixes

The anti-hallucination protocol stops you inventing findings. This section stops the three
*other* failure modes: laziness, rationalizing, and breaking code with careless fixes.

### Don't be lazy — actually look
- **Read the files, don't sample-and-guess.** A finding must rest on a line you read this
  session, not a pattern you assumed. "Looks like a typical Express app, so probably…" is a
  guess wearing a review's clothes.
- **Open the function you're suspicious about, and the ones it calls.** Taint flows cross
  function boundaries. Stopping at the first file is how real bugs get missed.
- **Follow the imports for any "defense".** A call to `validate()` / `is_safe()` /
  `sanitize()` proves nothing until you've read its body.
- **"I didn't find anything" is a claim you have to earn.** Before calling a file/diff clean,
  confirm you traced every entry point to its sinks. Only skimmed? Say "skimmed, not fully
  traced" — never imply coverage you didn't do.
- **Scale effort to risk, not convenience.** Auth, payments, crypto, deserialization,
  file/path handling, raw SQL, anything touching money or PII — slow, careful reading even
  when the diff is boring.
- **Ground claims in real numbers from the repo.** Not "this is O(n²)" — pull the actual
  scale: table sizes from migrations/seeds, batch sizes from config, list lengths from the
  caller. "On the `events` table (~5M rows per the migration) this nested loop is ~25M
  comparisons per request." A finding with a number is an order of magnitude more convincing
  and forces you to actually check.

### Don't rationalize — a real bug stays a bug
- **Never explain away a vuln to reduce your workload.** "Probably behind auth", "the caller
  likely validates", "not reachable in practice" — if you haven't *confirmed* the mitigation
  by reading it, the finding stands. Assumed mitigations are reported as assumptions.
- **Don't downgrade severity to avoid a hard conversation.** Severity follows
  `references/severity-rubric.md`, not how awkward the finding is.
- **Don't accept the code's own comments as proof.** `# input is already sanitized` is a
  claim to verify, not evidence.
- **Uncertainty is reported, not buried.** Can't tell if it's exploitable → a
  `needs verification` finding with the exact check, not a silent drop and not a fake CRITICAL.
- **The verification *step* is not optional; its *mechanism* tiers by host capability.**
  - **Tier A (preferred):** fresh-context subagent via `Task(...)` — the finding-verifier
    re-checks each finding in a context it didn't generate (Step 5c).
  - **Tier B (accepted substitute):** deterministic `verify_findings.py` + self-consistency
    re-derivation. A first-class fallback — it catches hallucinated files, missing quotes,
    bad line numbers.
  - **Tier C (minimum):** single-context self-review against the rubric, labelled
    lower-assurance in the report header. Tier C is the anchoring-prone case the whole
    design fights, so do it as a **forced re-derivation, not a re-read**: for each
    surviving CRITICAL/HIGH, discard your prior reasoning, open the file cold, and
    re-answer "is there a tainted source reaching this sink?" from the lines alone,
    without consulting your earlier write-up. A finding you can't reconstruct from the
    code this second time is downgraded or cut. It is weaker than a fresh process — say
    so in the header — but it is materially better than re-reading your own conclusion.
  Execution-grounding (Step 5d) is the strongest receipt when a PoC can be safely run.
  Take the highest tier the host supports and **state which tier ran**. When
  `verify_findings.py` says CUT, you cut; when it says RELOCATE, you fix the line number.

### Don't break meaning — fixes preserve intent (only when asked to apply)
- **Preserve behavior and intent.** A fix that closes the vuln but changes the return,
  drops a branch, or alters the contract is a *new bug*. State the invariant you're keeping.
- **Read the surrounding context first.** Match existing error handling, types, naming, and
  framework idioms. A parameterized query that ignores the file's DB helper is a worse fix.
- **Show before → after, minimally scoped.** Change the unsafe construct, not the whole
  function. Smaller diffs are easier to trust.
- **Name the regression risk.** Every fix ends with: "This could affect X — verify Y." If a
  fix needs a test, say which. Never present a fix as risk-free.
- **Don't fix what you don't understand.** Unclear intent → ask or flag; do not guess.

## Common false-positive patterns to NOT flag

First check `.review/suppressions.json` (a prior-resolved FP signature is default-suppress
unless you have new evidence). Then the universal patterns:

- **Tagged template literals in Prisma** (`` db.$queryRaw`SELECT ... ${id}` ``) — parameterized, safe. Only `$queryRawUnsafe` with a template literal is dangerous.
- **`dangerouslySetInnerHTML` with provably-sanitized input** (DOMPurify, sanitize-html, static source) — read the code to verify, then don't flag.
- **`subprocess.run([...], shell=False)`** with array args — not command injection (still consider whether the binary mistreats its own args).
- **`Math.random()` in cosmetic UI** — animation jitter, demo data — not a security issue. Flag only for tokens/IDs/anything security-relevant.
- **Public-by-design endpoints** (`/health`, `/version`) without auth — flag only if they leak secrets or internal state.
- **`==` of non-secret values** — only constant-time compare matters for secrets/hashes/tokens.
- **Unanchored regex used for matching (not validation)** — `re.search` is sometimes intentionally loose.

If you're about to flag something, ask: *"Could a junior dev push back on this with a valid
point?"* If yes, dig deeper to confirm, or downgrade and add "needs verification".
