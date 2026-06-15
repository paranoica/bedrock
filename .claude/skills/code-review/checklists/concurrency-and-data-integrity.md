# Concurrency & data-integrity checklist

Bugs that only appear under concurrent execution or that corrupt data. Read this
whenever there's shared mutable state, async/threads, transactions, money, or any
operation that can run more than once at the same time. Tools rarely catch these.

## Race conditions & TOCTOU
- **Check-then-act on shared state** is the core race. `if not exists: create`,
  `if balance >= amt: balance -= amt`, `get` then `set` — between the check and the act,
  another request can interleave. Needs an atomic operation, a lock, or a DB constraint.
- **TOCTOU on the filesystem:** `os.path.exists(p)` then `open(p)`; checking a file's
  permissions/owner then using it. The state can change in between. Prefer atomic ops
  (`open(..., 'x')`, `O_CREAT|O_EXCL`) and operate on fds, not re-resolved paths.
- **Read-modify-write without atomicity:** counters, inventory, balances updated by
  read → compute → write. Two concurrent runs lose an update. Use atomic DB updates
  (`UPDATE ... SET n = n + 1`), `SELECT ... FOR UPDATE`, optimistic locking (version
  column), or an atomic primitive (Redis `INCR`).

## Idempotency
- **Endpoints that cause side effects must tolerate being called twice.** Network
  retries, double-clicks, at-least-once queue delivery all replay requests. Payment
  capture, order creation, "send email", "provision resource" — look for an idempotency
  key, a dedupe table, or a unique constraint that makes the replay a no-op.
- **Webhook/queue consumers are at-least-once by default.** A consumer that isn't
  idempotent will double-process on redelivery. Flag missing dedupe.
- **Idempotency key must be stored before the side effect**, and the side effect made
  conditional on it — otherwise there's still a window.

## Locks
- **Lock ordering.** Acquiring locks A→B in one path and B→A in another = deadlock.
- **Lock scope:** holding a lock across a network call or a slow operation serializes
  everything and can deadlock with timeouts.
- **Distributed locks** (Redis `SETNX`, etc.) need a TTL (or a dead holder blocks
  forever) and fencing tokens (or a paused holder resumes and clobbers). A naive
  `SETNX` lock without TTL is a footgun.
- **Missing locks** where the comment assumes single-threaded but the deploy is multi-
  worker/multi-instance. "It's fine, only one process" is often false in prod.

## Transactions
- **Transaction boundaries too wide or too narrow.** A transaction that wraps an external
  HTTP call holds DB locks during network latency. A "transaction" that's actually
  several auto-committed statements isn't atomic at all.
- **Partial commit:** related writes that should be one unit but aren't in the same
  transaction → inconsistent state on failure between them.
- **Isolation level assumptions:** code that assumes serializability under READ COMMITTED.
  Phantom reads, lost updates, write skew. Money/inventory logic under the default
  isolation level often has a write-skew bug.
- **Long-running transactions** holding locks and bloating MVCC — perf + contention.

## Distributed data integrity
- **Dual writes** (write to DB *and* publish an event / call another service) with no
  outbox or compensation: one can succeed and the other fail, leaving the system
  inconsistent. Flag dual-write patterns; suggest transactional outbox or saga.
- **Non-idempotent backfills/migrations** that can't be safely re-run after a partial
  failure.
- **Ordering assumptions** on eventually-consistent reads or out-of-order message
  delivery.

## Money & precision
- **Floats for money.** `0.1 + 0.2 != 0.3`. Use integer minor units (cents) or a decimal
  type. Any `float`/`double`/JS `number` holding currency is a finding.
- **Rounding** applied inconsistently or at the wrong step (round once, at the end).
- **Currency mixing** without explicit conversion.

## Async-specific
- **Shared mutable state across async tasks / goroutines / threads** without
  synchronization. Closures capturing a loop variable. `await` between a check and a use,
  reintroducing a race even in single-threaded async.
- **Fire-and-forget** (`asyncio.create_task` / un-awaited promise / detached goroutine)
  whose errors vanish and whose completion nothing waits for.

## What NOT to flag
- Read-only concurrent access to immutable data.
- Check-then-act where a DB unique constraint already makes the act safe (read the schema).
- Single-run scripts and migrations explicitly run once under a human.
- Floats for non-money quantities where precision genuinely doesn't matter.
