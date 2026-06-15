# Thin language-module contract

Every file in `checklists/lang/` follows this shape. The flow reasoning lives in
`checklists/taint-spine.md` — modules do **not** repeat it. A module exists to give the
spine the language's concrete vocabulary. Keep it tight; depth comes from precision, not
length. `python.md` and `javascript-typescript.md` (in `checklists/`) are the deep
reference exemplars these are built to match.

## Required sections

1. **Header** — one line: the language + the frameworks/runtimes this covers.

2. **Sinks by S-category** — map the spine's S-categories (S1…S13) to this language's
   concrete functions/constructs. Only the categories that exist for this language. Each
   entry: the dangerous form (grep target) → the safe form. This is the highest-value part.

3. **Footguns** — language traps that cause real bugs *independent of taint* (logic/safety
   bugs, not style). Each: the trap, why it bites, the fix. Cap at the genuinely dangerous
   ones; no trivia.

4. **Sanitizer idioms** — the *correct* safe constructs a reviewer should expect to see, so
   a present-but-wrong defense is caught (Step 4/5 of the spine). Name the right escaper/
   parser/binding for each sink.

5. **Framework specifics** — for the common web frameworks in this language: the security
   defaults that are off, the dangerous escape hatches, the auth/ORM/template traps.

6. **Version notes** (when relevant) — footguns that exist or are fixed at specific runtime/
   framework majors, so the reviewer flags the version-appropriate issue.

## Rules

- **No invented APIs.** Every function/flag named must be real. When unsure, the module is
  built with a web-research pass on current footguns/CVE-classes for that language — never
  from memory alone. (This is the same anti-hallucination bar the skill applies to findings.)
- **Severity guidance, not severity hardcoding.** Point at `references/severity-rubric.md`;
  note where a category tends to land (e.g. memory-corruption → CRITICAL/HIGH), but the
  reviewer scores per-finding.
- **Client vs server threat model.** Client-side languages (Dart/Flutter, Swift, browser JS)
  have a *different* model — secrets in the bundle, insecure local storage, deeplink/IPC,
  cert-pinning, not server-side SQLi. State the model at the top.
- **Stay thin.** If you're re-explaining how taint flows, stop — that's the spine's job.
