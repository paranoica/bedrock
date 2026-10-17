# SQL, PostgreSQL, and Redis Checklist

For any code that talks to a relational database or Redis.

## SQL (any flavor)

### Schema design red flags
- `VARCHAR` without length, or absurd lengths like `VARCHAR(10000)` — flag and ask why.
- No `NOT NULL` constraints on fields that business logic assumes are always present.
- Money as `FLOAT` / `DOUBLE` — should be `NUMERIC(precision, scale)` or `DECIMAL`.
- Booleans stored as `INT` or `CHAR(1)` without clear convention.
- Enums as strings without DB-level CHECK constraint or enum type — invalid data sneaks in.
- Missing `FOREIGN KEY` constraints where relationships exist — orphaned rows accumulate.
- Tables without `PRIMARY KEY`.
- `CASCADE DELETE` on foreign keys without considering blast radius — one delete cascades through millions of rows.

### Query red flags
- `SELECT *` in production code paths (vs admin scripts) — flag.
- `WHERE 1=1 AND ...` — usually fine but smells like dynamic query building, check for SQLi.
- `OR` conditions on different columns — often kills index use; consider `UNION`.
- `LIKE '%foo%'` — leading wildcard prevents normal index use; consider full-text search (`tsvector`/`pg_trgm`).
- `NOT IN (subquery)` — NULL handling traps; prefer `NOT EXISTS`.
- `COUNT(*)` on huge tables in hot paths — use approximate counts or cached counters in Postgres.

### Indexing
- Queries from logs (`EXPLAIN ANALYZE` ideally) without supporting indexes — flag.
- Composite indexes: order matters. Index `(tenant_id, created_at)` serves `WHERE tenant_id=X ORDER BY created_at` well; `(created_at, tenant_id)` does not.
- Indexes on every column "just in case" — write amplification, wasted space.
- Functional indexes missed: `WHERE LOWER(email) = ...` needs `CREATE INDEX ... ON users (LOWER(email))`.
- Partial indexes underused: `WHERE deleted_at IS NULL` on most queries → partial index for active rows.

### Migrations
- `ALTER TABLE ... ADD COLUMN NOT NULL` without default → table rewrite + lock on big tables → downtime.
- `CREATE INDEX` without `CONCURRENTLY` (Postgres) → locks writes during build.
- Backfill in the same migration as schema change → long transaction holding locks.
- Dropping columns/tables still referenced by old app version during rolling deploy.
- Renaming columns without backwards-compatible step → downtime.

### Transactions
- Transactions wrapping external HTTP / external API → holds connection during network IO.
- `SELECT ... FOR UPDATE` without `NOWAIT` or `SKIP LOCKED` in queue-like consumers → contention or deadlock.
- Missing transaction where two writes need atomicity (debit one account, credit another).
- Mixing transaction with `autocommit` confusion in some drivers.

## PostgreSQL specifics

### Performance
- Missing `VACUUM` / `ANALYZE` planning — autovacuum config tuned for table sizes (default settings are bad for big tables).
- `SERIAL` vs `IDENTITY` vs `BIGSERIAL` — INT4 sequences run out (this happens). Use `BIGINT IDENTITY`.
- `text` is preferred over `varchar(n)` in Postgres unless length is a real constraint.
- `jsonb` indexed with GIN where queried by content; plain `json` if just storing.
- `array` types: useful but not always the right choice; relational table often beats it.

### Features that solve real problems
- `ON CONFLICT DO UPDATE/NOTHING` for idempotent inserts — preferred over check-then-insert race.
- `RETURNING` to avoid second SELECT after INSERT/UPDATE.
- Partial indexes (above) — huge wins on soft-delete schemas.
- Generated columns (`GENERATED ALWAYS AS`) for derived data.

### Common bugs
- Timezone confusion: `TIMESTAMP` vs `TIMESTAMPTZ` — almost always want `TIMESTAMPTZ`. Storing as naive `TIMESTAMP` is a perennial bug source.
- Case sensitivity: unquoted identifiers folded to lowercase; quoted preserved. Mixed = pain.
- `NULL` semantics in arithmetic and comparisons — `x = NULL` is always NULL, not true/false.

### Security
- Roles with more privileges than needed — connecting as superuser/owner from app code.
- `pg_hba.conf` allowing trust auth, or md5 only (should be `scram-sha-256`).
- `LISTEN/NOTIFY` payload trusted blindly by listeners — if pub source is multi-tenant, validate.
- Row-level security (RLS) policies — if used, verify they actually cover all access paths; `BYPASSRLS` privilege on app role defeats them.

## Redis

### Wrong tool for the job
- Used as primary storage for data you can't afford to lose (Redis without AOF + replication is best-effort).
- Used as a queue when you need durability — use Kafka/SQS/RabbitMQ instead, or Redis Streams with consumer groups + ack discipline.
- Used as a transactional store across multiple keys without `MULTI/EXEC` or Lua — race conditions.

### Performance killers
- `KEYS pattern*` in production code — O(N) blocking; takes the server down on large keyspaces. Use `SCAN`.
- `SMEMBERS`, `HGETALL`, `LRANGE 0 -1` on huge collections — blocks the single-threaded server. Use `SSCAN`/`HSCAN`/chunked reads.
- `FLUSHALL` / `FLUSHDB` reachable from any code path → catastrophic.
- Long Lua scripts blocking the event loop.
- Pipeline missing where many small ops happen sequentially.

### Memory & eviction
- No TTL on data that should expire → unbounded memory growth.
- `maxmemory` not configured / `maxmemory-policy noeviction` + insistent writes → OOM kills.
- Large values (multi-MB strings, huge hashes) → latency spikes.
- Storing redundantly serialized JSON when hash/zset would fit naturally.

### Caching patterns
- Cache key not including tenant/user where it should → cross-tenant cache leak (security).
- Cache key collisions across services using the same Redis → namespace your keys.
- Cache stampede on hot key expiry — singleflight / lock-and-fetch / stale-while-revalidate.
- Write-through without invalidation strategy after DB write → stale reads.

### Security
- Redis exposed on public network without `requirepass` and ACLs → trivial takeover (this has caused mass cryptominer infections).
- `CONFIG SET` reachable from app role → attacker can rewrite RDB to arbitrary location.
- `EVAL` with user input concatenated into script → Redis Lua injection (rare but real).

### Distributed locks
- Naïve `SETNX key value` for distributed lock without TTL → permanent lock on crash.
- Lock with TTL but no fencing token → stale lock holder can corrupt after expiry.
- Redlock is contentious; for most use cases a single Redis with TTL + fencing is enough — but be honest about the guarantees.

## ORMs over SQL

Whatever the ORM, you need to verify:
- Generated SQL is actually what you think (turn on query logging during review if possible).
- Lazy loading isn't causing N+1 (covered in performance.md).
- Raw escape hatches aren't being used carelessly (covered in injection-deep.md).
- Transactions / sessions are scoped per request, not global / per-app.

If reviewing migrations, check the actual generated SQL (`makemigrations --dry-run --verbosity 3` for Django, `alembic upgrade --sql` for Alembic) — autogenerated migrations sometimes do scary things.
