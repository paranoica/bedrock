# Migrations & backward-compatibility checklist

Default-on for **pr-review**, and any diff touching DB migrations, schema, or a public
API/response shape. The question is not "is this code correct" but "will this break
prod during deploy, or break a consumer". This is the highest-impact axis most LLM
reviewers skip entirely.

## Database migration safety (zero-downtime / rolling deploys)
Under a rolling deploy, **old and new code run at the same time** against the **new**
schema for a window. Every migration must be safe for that overlap.

- **Blocking locks on large tables.** `ALTER TABLE ... ADD COLUMN` with a volatile/`NOT
  NULL` default (older Postgres), `ALTER COLUMN TYPE`, adding a constraint without
  `NOT VALID` then `VALIDATE` — these can take an `ACCESS EXCLUSIVE` lock and stall all
  traffic. Flag long-locking DDL on big tables; suggest the online-safe form.
- **Index creation without `CONCURRENTLY`** (Postgres) locks writes for the duration.
- **`NOT NULL` column added without a default** breaks inserts from old code that doesn't
  set it. Safe pattern: add nullable → backfill → add constraint, across releases.
- **Dropping/renaming a column or table the currently-running old code still reads/writes.**
  Classic rolling-deploy outage. Safe pattern is expand/contract: add new → write both →
  migrate reads → stop writing old → drop, over multiple deploys. A drop in the same PR
  that introduces the replacement is almost always unsafe.
- **Renames** are drop+add to consumers. Treat `RENAME` as a breaking change.
- **Irreversible migrations** with no `down` / rollback path. If the deploy goes bad, can
  you roll back? A destructive migration with no recovery is a CRITICAL operational risk.
- **Backfills inside the migration transaction** that lock or run for minutes — separate
  data backfill from schema change; batch it.
- **Default value changes** that silently alter existing behavior for new rows.

## API / contract backward-compatibility
A change to anything a client depends on is a breaking change even if the code compiles.

- **Removing or renaming a response field**, narrowing its type, or changing its meaning.
- **Adding a required request field / param**, or making an optional one required, or
  tightening validation (stricter regex, narrower enum, lower max length) — rejects
  inputs that used to work.
- **Changing status codes, error shapes, pagination, default sort, or ordering** that
  clients parse.
- **Changing enum values** (removing/renaming) — consumers that switch on them break.
- **Default behavior changes**: a new default that flips existing callers' results.
- **Auth/permission tightening** on an existing endpoint that legitimate clients rely on
  (separately: auth *loosening* is a security finding — see security-general.md).
- **Serialization/format changes:** date format, number precision, null vs absent,
  timezone of timestamps.

For each: is there a version bump, a deprecation path, or a compatibility shim? If the
consumers are internal, are they in this repo (check them) or external (call it out as
a coordinated change)?

## Config & infra compatibility
- **Renamed/removed env vars or config keys** with no fallback — old deploys or other
  services break.
- **New required env var with no default** — deploy fails or behavior changes silently.
- **Message/event schema changes** consumed by other services (add-only is safe; removing
  or retyping a field is breaking) — same expand/contract discipline as DB.

## What NOT to flag
- Additive changes: new nullable column, new optional response field, new optional param,
  new endpoint, new enum value that old code ignores.
- Migrations on tables that are provably tiny/new (read the context).
- Internal-only functions with no external or cross-service consumers (confirm scope
  before assuming a contract exists).
- Breaking changes that are clearly intentional and coordinated (major version bump,
  explicit migration note) — still worth a one-line confirmation, not a CRITICAL.
