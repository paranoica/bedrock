# Severity & confidence rubric

Severity is assigned by this rubric, not by gut feel and not by how awkward the finding
is to raise. **Severity and confidence are separate axes** — never collapse them. A bug
can be CRITICAL-if-real but low-confidence; say both.

## Severity = Impact × Reachability × Exploitability

Think of severity as the product of three questions. A high score on one axis doesn't
make it CRITICAL if another axis is near zero.

**Impact — what happens if it fires?**
- Catastrophic: RCE, auth bypass, mass data exfiltration, data loss/corruption, payment
  loss, full prod-down.
- Severe: single-account takeover, injection with meaningful read/write, privilege
  escalation, sensitive data leak.
- Moderate: limited info disclosure, partial DoS, integrity bug with a workaround.
- Minor: cosmetic, log noise, self-DoS only.

**Reachability — can untrusted input actually get here?**
- Reachable from an unauthenticated public entry point: full weight.
- Reachable only from an authenticated/privileged path: reduce.
- Reachable only behind admin/internal network / feature-flag-off / dead code: heavily
  reduce. (Confirm reachability by tracing — don't assume "probably not reachable".)

**Exploitability — how hard is it to actually do?**
- Trivial (single crafted request, no preconditions): full weight.
- Needs specific conditions, timing (race), or chaining: reduce.
- Theoretical / requires already-privileged attacker: heavily reduce.

## Mapping to labels

- **CRITICAL** — Catastrophic impact, reachable from an untrusted path, trivial-to-
  moderate to exploit. The "fix before merge / this is how you get breached" tier. Also:
  known-exploited CVE in a reachable dependency; guaranteed data loss on a normal code path.
- **HIGH** — Severe impact and reachable, OR catastrophic impact gated behind one
  meaningful precondition (auth, a race, chaining). Likely-exploitable broken auth/authz.
  Severe perf regression that will take prod down under normal load.
- **MEDIUM** — Moderate impact, or severe impact that's hard to reach/exploit. Bad
  practice that will bite later. Missing validation with limited blast radius. Definite
  perf issue off the hot path.
- **LOW** — Minor impact, code smells worth fixing, missing tests on a risky path, minor
  perf. **No nitpicks rank above LOW**, and style/naming preferences are LOW or cut.

Tie-breakers: when between two labels, the deciding question is reachability from
untrusted input. Unreachable drops a tier; trivially reachable from the open internet
raises one.

## Confidence (orthogonal — always state it)

- **high** — you read the code, traced the flow, confirmed source reaches sink and the
  defense is absent/broken. The verifier returned VERIFIED. Ship it plainly.
- **medium** — strong evidence but one assumption unconfirmed (e.g. reachability you
  couldn't fully trace). State the assumption.
- **needs verification** — you suspect it but couldn't confirm. Include the **exact** check
  the reader should run. Better three high-confidence findings than ten half-guessed ones.

Report confidence inline: `**Confidence:** high` / `medium` / `needs verification — <check>`.

## Hard rules
- CRITICAL/HIGH must be a real bug or real vuln — never a style opinion.
- An unconfirmed mitigation never silences a finding; it lowers confidence, not severity.
- A finding the verifier (Step 5c) cut does not come back at a lower severity. It's gone.
- Dependency CVEs use their **computed** band from `check_cves.py` (CVSS-derived), not a
  blanket CRITICAL — but a reachable, known-exploited CVE is CRITICAL regardless of band.
