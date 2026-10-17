# Privacy & data-flow checklist

Trace PII not to an *exploit* sink, but to where it legitimately-but-wrongly ends up:
logs, analytics, third parties, the wrong region, or kept too long. This is a
regulatory/contract axis (GDPR/CCPA/HIPAA-style), not OWASP, and grep won't find it —
you have to follow the data. Read when the code handles personal data.

## What counts as PII / sensitive data
Names, emails, phone, address, IP, device/advertising IDs, precise geolocation,
government IDs, financial/account numbers, health data, biometrics, auth tokens,
and anything that re-identifies a person in combination. Treat free-text user content
as potentially containing PII.

## Leaks into the wrong sink
- **PII in logs.** `logger.info(user)`, logging full request bodies/headers, stack
  traces that include params, `print(payload)`. Logs get shipped to third parties and
  kept for ages — a top real-world privacy failure. Flag logging of identifiers, tokens,
  full objects, or request/response dumps on PII paths.
- **PII in analytics / telemetry / error trackers.** Sending email/user-id/IP to
  Segment, GA, Sentry, Datadog, Mixpanel, etc. without scrubbing. Sentry `before_send`
  not stripping PII; analytics events with raw identifiers.
- **PII to third parties / sub-processors.** Data sent to an external API (LLM provider,
  enrichment, payment, email vendor) that the user didn't consent to or that isn't a
  declared processor. Flag new outbound calls carrying personal data.
- **PII in URLs / query strings** (logged by proxies, stored in history, leaked via
  Referer), in cache keys, in error messages returned to other users.
- **Over-collection / over-exposure:** an API returning more fields than the caller
  needs (full user object where an id+name would do), `SELECT *` serializing internal
  PII columns to clients.

## Residency & cross-border
- **Data residency:** PII routed to storage/compute in a region that violates a
  residency requirement (EU data leaving the EU, etc.). Flag region-specific buckets/DBs
  being bypassed, or a new vendor in another jurisdiction.
- **Cross-tenant / cross-region replication** of personal data without controls.

## Retention & deletion
- **Retention:** personal data written to a store with no TTL/expiry/retention policy
  where one is expected (raw logs, event tables, soft-deleted rows kept forever).
- **Right-to-delete completeness:** a "delete user" path that misses copies — caches,
  search indexes, analytics, backups-references, denormalized tables, third parties,
  message queues. If deletion only hits the primary table, that's an incomplete erasure.
- **Soft-delete that still exposes** the row to queries/exports.

## Consent & purpose
- Using data for a purpose beyond what it was collected for (e.g. support email reused
  for marketing) where consent matters.
- Missing consent gate before tracking/telemetry fires.

## Encryption & access
- Sensitive fields stored in plaintext where encryption-at-rest/field-level encryption
  is expected (note: this overlaps security-general — flag once, in the more specific
  place).
- PII accessible without an authorization check (overlaps IDOR — flag once).

## What NOT to flag
- Pseudonymous internal IDs that don't map to a person without a separate join you've
  confirmed is protected.
- Aggregate/anonymized metrics with no re-identification risk.
- Logging non-personal operational data (timings, status codes, opaque request ids).
- Region/retention concerns on clearly non-personal data.
