# Report Template

The exact format the review output must follow. Render this directly into the chat.

## Structure

```
# Code Review — <project name or PR ref or "uncommitted changes">

**Scope:** <files reviewed, line count>
**Stack detected:** <e.g., Node 20 + Next.js 15, Python 3.12 + FastAPI, PostgreSQL>
**Tools run:** <semgrep, gitleaks, bandit, OSV.dev>  *(say which were skipped)*
**Verification:** tier <A: fresh-context subagent · B: deterministic verifier + self-consistency · C: single-context self-review (lower assurance)> · `verify_findings.py`: VERIFIED=<n> RELOCATE=<n> CUT=<n> NEEDS_HUMAN=<n> · receipt:<12-hex>
  *(This line is MANDATORY and machine-checked by `scripts/check_report.py`. The counts AND the `receipt:<12-hex>` id are the literal output of the verifier run on `findings.json` — never typed from memory; `check_report.py --receipt .review/verify-receipt.json` re-hashes the cited source files from disk, so a hand-written line cannot pass. No counts here = the grounding gate (Step 5c) did not run, and the report is incomplete. Never claim a tier you didn't run — see invariants 12. **`VERIFIED` here means grounded — the line is real and quoted — not proven exploitable; the receipt is anti-hallucination, not a correctness proof.**)*

---

## Coverage & limits

*(2-4 lines, always present, never skipped — this is what keeps "no findings" honest.)*
State plainly what was actually examined and what wasn't: files read in full vs only skimmed; checklists loaded; tools that ran vs were unavailable (degraded mode); OSV reachable or skipped. Then the recall caveat in one line: **this review grounds what it found (precision) and cannot certify what it didn't (recall) — "no CRITICAL findings" means none were found in what was reviewed, not a proof the code is safe.** A clean result with skipped scans is reported as "clean under X, with Y not covered," never as "clean."

---

## Vulnerable dependencies

*(omit this section if no CVEs found)*

- **`<package>@<version>`** — `<CVE-id / GHSA-id>` — <severity from advisory> — <one-line summary>
  Fix: upgrade to <version range> per advisory.

*A row with severity `REVIEW` means OSV shipped a CVSS vector the offline scorer couldn't compute (typically a CVSS 4.0-only advisory). It is NOT low-risk — surface the carried `cvss_vector`, score it by hand (or note the `cvss` lib is needed), and band it. Never drop a REVIEW row as "clean."*

---

## CRITICAL

### Title in plain English (not "Issue 1")
**File:** `path/to/file.ext:42`
**Category:** <SQL Injection / Auth Bypass / Crypto / etc.>

```language
[5-10 lines max of offending code]
```

**Problem:** One paragraph. What's wrong, how it gets exploited, what an attacker reaches. No hedging on real findings.

**Fix:**
```language
[concrete code, 1-5 lines]
```

**Refs:** OWASP A03:2021 / CWE-89 / <link if external>

---

### [next CRITICAL finding...]

---

## HIGH

[same format]

---

## MEDIUM

[same format; can be slightly terser]

---

## LOW

*Style/maintenance issues only worth fixing in passing. Group several into one block if related.*

- `file.ext:12` — short description — short fix
- `file.ext:88` — short description — short fix

---

## Improvements

*The upside pass. Things that work but could be better. NOT bugs. Limit 5-7. If nothing qualifies under the strict rules in checklists/improvements.md, the section is exactly one line, in the user's language (EN: "Code clean — nothing substantial to suggest." / RU: "Код чистый — ничего существенного не предложу.").*

### [HIGH IMPACT / MEDIUM IMPACT / LOW IMPACT] Short title
**File:** `path/to/file.ext:42`
**Category:** Speed / Memory / Readability / Architecture / Modern API / Observability

```language
[current code, max 5 lines]
```

**Why:** One paragraph. What this gives you. Cite scale where possible ("10x on lists >1k", "removes round-trip on hot path"). No vague "more idiomatic".
**Suggested:**
```language
[improved code, max 5 lines]
```

*(repeat for each improvement, max 5-7 total)*

---

## What's actually good

*One short paragraph. Only include if something is genuinely well-done. Skip the section entirely otherwise. Do NOT pad this.*

---

## Verdict

2-3 lines. Direct. Examples:

- "Не merge. Один CRITICAL и три HIGH — SQLi на `/api/search` и сломанный CSRF на админских роутах. Чини сначала эти, остальное потом."
- "Merge после фиксов в HIGH. CRITICAL нет, но IDOR в `/api/orders/:id` обязателен. MEDIUM можно отдельным PR."
- "Готово к merge. Один MEDIUM, остальное LOW. Хороший код."

If the user asked in Russian, write the report in Russian. If English, English. Match their language.
```

## Rules for the report

1. **No emojis anywhere.** Not in headings, not in bullets, not at the end. None.
2. **No "Хочу отметить..."** padding. Get to the finding.
3. **No false equivalence:** if there are 0 CRITICAL findings, don't invent one to look thorough. If everything is LOW, say so honestly.
4. **Counts in the summary:** "3 CRITICAL, 5 HIGH, 11 MEDIUM, 4 LOW" — give the user a quick scan.
5. **Severities are calibrated:**
   - CRITICAL = exploitable now, real damage, or production-down risk
   - HIGH = exploitable with conditions OR severe perf/correctness
   - MEDIUM = real issue but not immediate-fire
   - LOW = code smell, minor cleanup, missing-but-not-critical
6. **If you flag something as CRITICAL/HIGH, you need to be able to defend it.** Reviewer credibility comes from not crying wolf. If you're 50/50 whether it's exploitable, it's MEDIUM with "needs verification."
7. **Length:** the report should be as long as it needs and no longer. A clean PR with one HIGH finding = 30-line report. A messy full-project audit = several screens. Do not pad to look thorough.
