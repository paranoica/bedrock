# Removed-defenses checklist (review of absence)

Most review looks at what code *does*. This looks at what a diff *removes* or *weakens*.
Deleting a guard is invisible to "is this line correct" review, and it's a recurring way
prod breaks and vulns get reintroduced. Run on **uncommitted** and **pr-review** modes,
reading the diff's deletions (`-` lines), not just additions.

## Read the minus lines
Go through everything the diff deletes or changes-away. For each removed/weakened
protection, the bar is: **the PR must justify the removal.** If it doesn't, that's the
finding — "this removes X; why?" — at the severity of what X protected.

## Security guards removed / weakened
- **Auth / authorization check deleted** from an endpoint or function (decorator,
  middleware, `if not user.can(...)`, permission gate). CRITICAL unless clearly moved
  elsewhere — confirm it's actually relocated, not gone.
- **Input validation / sanitization removed** (schema check, allowlist, escaping,
  `validate()` call) on a path that still reaches a sink.
- **Validation loosened:** regex made more permissive, length/range cap raised or dropped,
  enum widened, type check removed, `strict` turned off.
- **CSRF/CORS/security-header protection removed or relaxed** (CORS opened to `*`,
  `SameSite` dropped, CSP weakened, `secure`/`httpOnly` removed from a cookie).
- **Crypto weakened:** stronger algo/params swapped for weaker, constant-time compare
  replaced with `==`, randomness source changed to a non-CSPRNG, verification disabled
  (`verify=False`, `verify_exp=False`, cert checks off).
- **Rate limit / quota / size cap removed** (request size, upload limit, pagination cap,
  throttle) — opens DoS / resource exhaustion.

## Reliability guards removed
- **Timeout / retry / circuit-breaker removed** (ties to resilience.md) — reintroduces
  hang/cascade risk.
- **Error handling removed:** a `try/except`/`catch` deleted, a rollback removed, a
  `finally` cleanup dropped, an error check turned into a swallow.
- **Transaction / lock removed** around a multi-step or shared-state operation (ties to
  concurrency-and-data-integrity.md).
- **Null/empty/bounds check removed** before a deref/index/slice.

## Correctness guards removed
- **Assertion / invariant check deleted** from a critical path.
- **Feature flag / kill switch removed** that was protecting a risky path.
- **Idempotency key / dedupe removed** from a side-effecting op.

## Tests & observability removed
- **Test deleted or skipped** (ties to test-quality.md) — possibly because it was failing
  on the new (wrong) behavior.
- **Logging/metric/alert on a critical path removed**, reducing the ability to detect the
  next incident.

## How to confirm it's really gone (not just moved)
For each removal, search the codebase for the protection elsewhere before flagging:
- Was the auth check pushed into middleware / a parent route? Read it.
- Was validation centralized into a schema? Confirm the schema covers it.
If you can show it moved and still covers the path, it's not a finding. If you can't, it
is — assume removed-until-proven-relocated, the opposite of the usual benefit of the doubt.

## What NOT to flag
- Removals that are clearly part of a justified refactor where the protection demonstrably
  moved and still applies (you verified it).
- Dead/duplicate guards being cleaned up where another correct guard remains on the path.
- Loosening that's intentional and safe (e.g. a validation that was wrong/too strict),
  when the PR explains it — still worth a one-line confirmation, not a CRITICAL.
