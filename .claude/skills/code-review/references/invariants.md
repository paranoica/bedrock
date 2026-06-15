# Invariants — re-read at the start, before findings.json, and at the grounding gate

The compact, non-negotiable core. Short by design so reinjection is cheap. The full
reasoning behind each line is in `references/review-discipline.md` — pull that only at
the verification gate or before applying a fix.

## Output discipline
1. **Harsh, specific, useful.** Every finding: severity · `file:line` · why it's broken · concrete fix. No "consider maybe perhaps".
2. **No nitpicks above MEDIUM.** Style/naming/"I'd write it differently" = LOW or cut. CRITICAL/HIGH must be a real bug or real vuln.
3. **Praise is forbidden unless earned.** Open with the worst finding, not "great work".
4. **One quote per finding, ≤10 lines.** Quote the *actual* code verbatim, then explain.
5. **Don't inflate the count.** Same root cause on adjacent lines = one finding with a range.

## Truth discipline (the failure modes that kill credibility)
6. **No hallucinated findings.** Never invent CVE/GHSA IDs, line numbers, package versions, or library vulns. Only cite CVEs from OSV output or this session's web search. Uncertain → `Confidence: needs verification — <exact check>`, never a fake CRITICAL and never a silent drop.
7. **Read, don't guess.** A finding requires a line you read this session, not a pattern you assumed. Follow the flow across files; read the body of any `validate()/sanitize()/is_safe()` before trusting it.
8. **Don't rationalize a bug away.** "Probably behind auth / caller validates / not reachable" is an assumption to *confirm by reading*, not a reason to drop or downgrade. Comments lie; code doesn't.
9. **Tool findings are leads, not findings.** Verify every semgrep/bandit hit against the source; drop false positives.

## The finding rule (taint-spine)
10. **A finding = tainted source AND unsafe sink in the same flow.** Hardcoded source or provably-safe sink (parameterized, schema-validated, allowlisted) = not a finding. Prove the defense holds against a concrete worst-case input, don't assume "a fence exists".

## Verification is mandatory (mechanism tiers; the step never skips)
11. **Every finding carries a checkable receipt.** Before the report: emit `findings.json`, run `scripts/verify_findings.py` (it writes a hash-bound `.review/verify-receipt.json`). Honor verdicts: `CUT_*` → delete; `RELOCATE` → fix lines; `NEEDS_HUMAN` → keep as needs-verification; `VERIFIED` → ship. When it says CUT, you cut — you don't argue the line back in. **`VERIFIED` means the cited line is real and quoted exactly — NOT that the vuln claim is correct.** The harness grounds *existence*, not *exploitability*: a confidently-wrong finding on a real line passes it green. That is what tier 12 is for — and even the fresh-context re-check shares your *evidence* (same files, same findings.json), so a subtle false claim can survive both. In the report, never let `VERIFIED` read as "true"; it reads as "grounded". The Verification line carries the receipt's `receipt:<12-hex>` id; `check_report.py --receipt` re-hashes the cited files from disk so the counts can't be hand-forged.
12. **Then re-check in a context that didn't generate the finding** (Tier A: `Task` subagent / Tier B: deterministic verifier + self-consistency / Tier C: single-context self-review, labelled lower-assurance). State which tier ran in the report header.

## Fixes (only when asked to apply)
13. **Preserve behavior and intent.** State the invariant you're keeping. Smallest scope. End every fix with one line: "This could affect X — verify Y." Never present a fix as risk-free; don't fix what you don't understand.

## Honesty about coverage
14. **A skipped scan is a stated gap, never "clean".** OSV unreachable / tool missing / file only skimmed → say so in the report header, mark affected findings lower-confidence. Never imply coverage you didn't do. **Precision is not recall:** the harness grounds what you *found* (cuts hallucinations), it does not prove you found everything. "No CRITICAL findings" = none surfaced in what was reviewed, not a safety proof. Every report carries the Coverage & limits block stating what was and wasn't examined.
