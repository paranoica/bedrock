# Pack: Background jobs

## Rules
- Every job is idempotent: running it twice gives the same result as once.
- A job records progress, so a restart resumes instead of starting over.
- Retries with backoff and a cap; a dead-letter place for jobs that keep failing.
- Time limits on every job; no job holds a lock it might not release.

## Critical zones to consider
Schedulers, queues, anything that sends messages or moves money.

## Reviewer checklist
- What happens when the job dies halfway (kill -9 at each step).
- Duplicate delivery from the queue.
- Clock and timezone of schedules; daylight saving changes.

## Test checklist
- Run twice, run concurrently, kill mid-run and resume.
- A poison message does not block the queue.
