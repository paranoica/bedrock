# Resilience checklist

Failure-mode review. What does this code do when a dependency is slow, down, or
returns garbage? These bugs cause more prod incidents than exotic injections, and
static tools almost never catch them. Read this on every review.

## Timeouts
- **Every network/IO call has an explicit timeout.** No timeout = a hung downstream
  pins a thread/connection forever and the failure cascades. Check HTTP clients, DB
  drivers, cache clients, message brokers, gRPC.
- Default-infinite offenders to flag: `requests` without `timeout=`, `fetch` without an
  `AbortController`/signal, `http.request` without `timeout`, raw sockets, DB pools with
  no `statement_timeout` / `connect_timeout`.
- Timeout should be **shorter** than the caller's timeout. A 30s inner call inside a 10s
  request handler is a guaranteed 504 with a wasted worker.

## Retries
- **Retries need backoff + jitter.** Fixed-interval or immediate retries against a
  struggling service create a retry storm that turns a blip into an outage.
- **Retries need a cap** (max attempts) and a budget. Unbounded retry loops are a DoS
  on your own infra.
- **Only retry idempotent operations.** Retrying a non-idempotent POST = double charge,
  duplicate row, double email. If it isn't idempotent, it needs an idempotency key
  (see concurrency-and-data-integrity.md), not a retry.
- **Don't retry non-retryable errors.** 400/401/403/422 won't fix themselves; retrying
  them wastes time and hides the real error.

## Circuit breaking & backpressure
- A repeatedly-failing dependency should be **short-circuited** (circuit breaker), not
  hammered on every request. Absence isn't always a bug, but for hot-path calls to
  flaky services, flag it.
- **Bounded queues / concurrency limits.** Unbounded in-memory queues, `Promise.all`
  over an unbounded list, spawning a goroutine/task per item with no limit → memory blowup
  under load. Look for fan-out without a semaphore/pool.
- **Load shedding:** under overload, is there any path that rejects fast instead of
  accepting work it can't finish?

## Partial failure & cleanup
- **Multi-step operations that can fail midway need cleanup or compensation.** Wrote to
  DB then the email send throws — is the DB row left in a bad state? Look for missing
  `try/finally`, missing transaction rollback, orphaned resources (temp files, file
  handles, locks, DB connections) on the error path.
- **Resource release on every path.** Open without a `with` / `defer` / `finally`.
  Acquired locks not released on exception. Connections not returned to the pool.
- **Error swallowing.** `except: pass`, `catch {}`, `.catch(() => {})`, ignored error
  returns in Go. A swallowed error on a write path is silent data loss. Flag it —
  this is also a `llm-slop.md` smell.

## Graceful degradation
- Cache/optional-dependency down → does the app fail hard or degrade? A Redis outage
  should not 500 the whole site if the cache is just an optimization.
- Feature behind a flag → does the off path actually work, or is it dead/untested?

## Health & shutdown
- **Readiness vs liveness** conflated: a liveness probe that checks a downstream will
  kill the pod when the downstream blips. Liveness = "am I alive", readiness = "can I
  serve".
- **Graceful shutdown:** on SIGTERM, are in-flight requests drained, connections closed,
  consumers unsubscribed? Abrupt exit mid-request = partial writes and client errors.

## What NOT to flag
- Missing circuit breaker on a one-off startup call or a script — breakers are for
  hot paths, not every call.
- Missing timeout on a localhost call in a CLI tool with a human watching.
- Retries absent where the caller above already handles them (read up the stack first).
