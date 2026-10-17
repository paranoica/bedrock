# GraphQL — API security checklist

Covers GraphQL servers (Apollo, graphql-js, Hasura, Strawberry/Graphene, gqlgen, etc.). The
core difference from REST: **one endpoint, client-controlled query shape, and no authorization
by default** — every resolver must secure itself. Built on the spine (injection still happens
in resolvers). ~80% of GraphQL APIs fail to address the DoS surface.

## GraphQL-specific findings

- **Introspection enabled in production** — exposes the entire schema (every type, field,
  relationship) → an attacker maps the whole attack surface. Disable in prod (or role-restrict,
  e.g. Hasura) unless the API is intentionally public.
- **No depth / complexity limit (DoS)** — a deeply nested or recursive query
  (`user → posts → author → posts → …`) or a "complexity bomb" (cheap-looking, heavy to
  resolve) generates millions of DB hits → resource exhaustion. Require depth limiting (≈5–10),
  a complexity/cost budget, and per-query timeouts.
- **Batching / aliasing bypasses rate limiting** — multiple operations in one HTTP request, or
  the same field requested under many aliases, defeats request-level rate limits and enables
  **2FA/OTP brute-force and credential stuffing** in a single call. Count operations/aliases
  toward limits; cap batch size; consider persisted/allowlisted queries.
- **Field-level authorization gaps** — authz applied at the query entry but not in individual
  resolvers, so a nested or alternate path returns objects/fields the user shouldn't see (a
  GraphQL-flavored IDOR / over-exposure). Enforce authz **in each resolver**, on each sensitive
  field, including nested relations.
- **Verbose errors / debug mode** — stack traces, DB errors, or Apollo tracing/debug enabled in
  prod leak internals; mask errors to the client.
- **CSRF on mutations** — a GraphQL endpoint accepting `application/x-www-form-urlencoded` or
  simple-content-type POSTs is CSRF-able; require a non-simple content type / CSRF token /
  SameSite cookies.
- **WebSocket subscriptions** — missing origin check (CSWSH) and per-message auth on the
  subscription transport.

## Injection (resolvers — the spine still applies)

A resolver that builds a DB query/command from arguments has the same S1/S2/S3 injection as any
handler — **arguments are tainted input**. Parameterize in the resolver; validate every
argument with schema constraints (`graphql-constraint-directive`: length, range, enum, format).
SSRF (S8): a resolver that fetches a client-supplied URL needs the same allowlist as anywhere.

## What "safe" looks like

- Introspection off (or role-gated) in prod; errors masked; debug/tracing off.
- Depth limit + complexity/cost analysis + query timeout; batch-size cap; operation/alias counting
  in rate limits; persisted queries for sensitive apps.
- Authorization enforced per resolver and per sensitive field, on nested paths too.
- Parameterized resolver queries; declarative argument validation; SSRF allowlist on outbound
  resolver calls; CSRF protection + WebSocket origin/auth checks.

Cross-refs: resolver injection mechanics → `checklists/taint-spine.md`; cost/DoS framing →
`checklists/resilience.md` and `checklists/finops.md`.
