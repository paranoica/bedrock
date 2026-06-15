# Performance Checklist

Performance issues that actually matter in production. Skip the micro-optimization noise (`for` vs `forEach`, `let` vs `const`). Focus on order-of-magnitude wins.

## 1. Database

### N+1 queries
The classic. Look for:
- Loop containing a query: `for user in users: user.posts = Post.objects.filter(user=user)` → 1 + N queries.
- ORM lazy loading without `select_related` (Django), `joinedload` (SQLAlchemy), `include` (Prisma), `populate` (Mongoose).
- Resolvers in GraphQL hitting the DB per item without DataLoader.

**Fix:** eager loading / batched fetch / DataLoader. Always.

### Missing indexes
- `WHERE` clauses on unindexed columns in tables expected to grow
- `ORDER BY` on unindexed columns
- Composite indexes: query on (a, b, c) needs index on `(a, b, c)` in that order, not three single indexes
- Foreign keys without indexes (Postgres doesn't auto-index FKs)
- Look at migration files for what's actually indexed vs what's queried

### SELECT *
- Pulling 50 columns when 3 are needed wastes bandwidth and memory. In hot paths, flag.
- ORM equivalents: `.all()` returning full objects with relations.

### Pagination
- Offset pagination on large tables → quadratic cost. After page 100, the DB scans 100*N rows.
- Cursor / keyset pagination for anything that might exceed a few thousand rows.

### Transactions
- Long transactions holding locks → contention.
- Transactions wrapping external HTTP calls — disaster, blocks DB connection during network IO.
- Missing transaction where atomicity is required (two related writes, only one might succeed).

### Connection pooling
- Per-request DB connection creation → connection storm. Use pgbouncer / built-in pool.
- Pool size mismatch between app and DB.

## 2. Caching

### Missing cache
- Repeatedly computed expensive values per request: config parsing, JWT public key fetch, feature flag lookups, permission expansion.
- Static-ish data fetched fresh every time: country lists, plan tiers.

### Cache stampede
- Many requests miss the cache simultaneously when it expires → all hit the backend at once.
- Fix: lock-around-fetch (singleflight), probabilistic early expiration, or stale-while-revalidate.

### Cache invalidation
- Writes don't invalidate the cache → stale reads.
- Cache keys not scoped by tenant/user → cross-tenant data leak (this is a SECURITY issue too).

### Redis specifics
- `KEYS *` in production code — O(N) blocking command, takes the server down at scale. Use `SCAN`.
- `HGETALL` on hashes with thousands of fields — same blocking issue.
- No TTL on data that should expire → memory bloat indefinitely.

## 3. Network / IO

### Synchronous HTTP in async handlers
- Node: `await axios.get(...)` inside a request handler called by 10k req/s — fine if remote is fast, disaster otherwise. Need timeouts, circuit breakers.
- Python async: `requests.get(...)` (sync) inside `async def` → blocks the event loop. Use `httpx.AsyncClient` or `aiohttp`.

### Missing timeouts
- `fetch(url)` with no timeout — hangs forever if remote is slow. Flag every external call without a timeout.
- DB query timeouts — long queries should be capped.

### Sequential requests that could be parallel
```python
# BAD
a = await fetch_a()
b = await fetch_b()
c = await fetch_c()
# GOOD
a, b, c = await asyncio.gather(fetch_a(), fetch_b(), fetch_c())
```

### Streaming vs buffering
- Reading a large file fully into memory before sending → memory spike. Stream it.
- Building a giant JSON response in memory for huge collections — stream / paginate.

## 4. Memory & allocations

### Loading everything into memory
- `.all()` / `SELECT *` returning millions of rows → OOM. Use iterators / cursors / chunks.
- File processing: `file.read()` vs streaming line-by-line.

### Memory leaks
- Event listeners attached but never removed (Node, React)
- Closures holding references to large objects unintentionally
- Caches without size limits → grow forever

### Hot loops
- Allocating new objects inside tight loops where reuse is possible
- String concatenation in a loop in Python (`s += x` repeatedly) — use `"".join(parts)`
- In JS: array creation/spread inside hot loops in render paths

## 5. Frontend (when reviewing React/Next)

### Re-render storms
- New object/array/function literal as prop every render → child re-renders.
- Missing `useMemo`/`useCallback` on expensive computations passed to memo'd children.
- `useEffect` dependencies missing → stale closures, or extra → effect spam.

### Bundle size
- Large libraries imported wholesale: `import _ from 'lodash'` vs `import debounce from 'lodash/debounce'`
- Server-only code accidentally bundled to client
- Moment.js (deprecated, huge) — flag, recommend date-fns/luxon

### N+1 fetching
- `useEffect` per list item fetching its own data → use a batched endpoint
- React Query / SWR without proper key strategy → refetch storms

### Images
- No `<img loading="lazy">` for below-fold images
- Unoptimized images in Next.js (`<img>` instead of `<Image>`)
- Missing `width`/`height` causing CLS

## 6. Algorithmic

- O(n²) where O(n) or O(n log n) is possible — nested loops over the same array, repeated `.includes()` instead of Set.
- Repeated sort/filter on the same data in a loop
- Regex compiled inside hot loops (compile once, reuse)

## 7. Concurrency

- Race conditions on shared state without locks (file writes, in-memory counters, "check then set" patterns)
- Database "check then insert" without unique constraint or `ON CONFLICT` → duplicate rows under load
- Optimistic vs pessimistic locking choice missing where contention is expected
- **TOCTOU on filesystem:** `if os.path.exists(path): open(path, 'w')` — attacker can create a symlink between the check and the open. Use `O_CREAT | O_EXCL` flags or just attempt the operation and handle the conflict.
- **Business-logic races:** "fetch balance, compute new balance, write" without transaction → lost update. Same with inventory deduction, vote counters, "first to claim wins" promotions. Demand `SELECT FOR UPDATE`, optimistic concurrency with version columns, or atomic DB operations (`UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1`).
- **Webhook idempotency:** processing webhooks without idempotency keys → duplicate processing on retries. Demand a dedup table or idempotency key check.
- **Distributed locks with TTL but no fencing token:** the lock holder can lose the lock (TTL expiry) without knowing, two holders run simultaneously. Either use fencing tokens or accept the risk and design for idempotence.


## How to write perf findings

Be quantitative when possible:
- "This N+1 issues N queries per request — at 50 items per page and 100 req/s, that's 5000 extra queries/s"
- "SELECT * on the orders table returns ~2KB/row; for 1000 rows that's 2MB per response when 200 bytes would suffice"

If you can't be quantitative, at least describe the scale at which it bites: "fine at 100 users, dies at 10k."

Severity guidance:
- **CRITICAL**: app-down risks, OOM patterns, quadratic algorithms in user-facing paths, missing-timeout that can cascade
- **HIGH**: N+1 in hot paths, blocking calls in async event loops, missing critical indexes
- **MEDIUM**: caching gaps, smaller N+1s in cold paths, mild allocation issues
- **LOW**: micro-optimizations, bundle size cleanups
