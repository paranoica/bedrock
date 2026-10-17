# FinOps / cost-regression checklist

Code that is correct, secure, and fast can still quietly double the cloud bill. Almost
nobody reviews for "this PR makes us pay more", yet cost blow-ups are a real recurring
incident class. Read on infra-touching or data-volume-touching changes. Frame findings
as cost risk with a rough driver, not a security severity.

## Network / data transfer
- **Cross-AZ / cross-region traffic** introduced on a hot path (chatty service in AZ-a
  calling a DB/replica in AZ-b; reading from a bucket in another region). Inter-AZ and
  egress bytes are billed per GB and add up fast.
- **Egress to the internet / to another cloud** added in a loop or per-request (calling
  an external API per item, shipping large payloads out).
- **Missing/disabled compression** on large responses or inter-service payloads.
- **Chatty N+1 across the network** (not just DB): per-item HTTP/gRPC calls where a batch
  endpoint exists — costs latency *and* request-priced calls.

## Polling & schedulers
- **Tight polling loops** against a paid API or cloud service (polling every second where
  events/webhooks/backoff would do) — multiplies request charges 24/7.
- **Cron/schedule frequency** bumped without thinking about per-run cost (a job that spins
  up compute every minute).
- **Busy-wait / no backoff** that keeps a worker (and its billed compute) hot.

## Storage & logging volume
- **Log explosion:** verbose/debug logging on a hot path, logging full payloads, per-row
  logging in a loop. Ingestion + retention in Datadog/CloudWatch/etc. is volume-priced —
  a debug log left in a request handler is a recurring bill.
- **Unbounded retention / no lifecycle policy** on buckets, log groups, snapshots, tables
  that grow forever.
- **Writing large blobs to expensive stores** (putting big objects in a DB/row store
  instead of object storage), high-write-amplification patterns.
- **Per-request temp artifacts** not cleaned up (disk/object accumulation).

## Compute & serverless
- **Holding a connection/resource open in serverless** (Lambda keeping a DB connection or
  doing long sleeps) — billed for idle wall-clock.
- **Over-provisioned memory/timeout** defaults copy-pasted, or **infinite/large retries**
  that re-run billed work.
- **Fan-out without a cap** spinning up unbounded parallel tasks/containers.
- **Cache removed or TTL slashed**, pushing load (and per-call cost) onto a paid backend
  or recomputation.

## Managed-service specifics
- Switching a query to a pattern that triggers full scans on a scanned-bytes-priced
  engine (Athena/BigQuery `SELECT *` / no partition filter).
- Provisioned throughput / autoscaling ceilings raised silently.

## How to estimate (ground it)
Where possible, attach a rough driver: "per-request egress × request volume", "polls/day
× price-per-call", "log lines/req × bytes × ingest price". A number, even approximate,
makes the finding actionable. Pull request volume / table sizes from configs or
migrations if available.

## What NOT to flag
- One-off scripts, migrations, or admin tools where cost is negligible.
- Micro-optimizations with no realistic volume behind them.
- Cost trade-offs that are clearly intentional and worth it (a cache that costs RAM to
  save a slow query) — note only if the trade looks wrong.
