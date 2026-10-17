# Pack: Databases

## Rules
- Every schema change is a migration with a tested down path, or a written reason it has none.
- Migrations on shared environments are outward actions: the owner's grant (D016).
- Long migrations run in batches; no full-table lock on a hot table.
- Queries use parameters; no string-built SQL.

## Critical zones to consider
`migrations/**`, the schema files, data backfill scripts.

## Reviewer checklist
- Indexes for new filters and joins; an `EXPLAIN` for queries on large tables.
- N+1 queries in loops.
- Transactions around multi-step writes; isolation level stated where it matters.
- Nullability and defaults of new columns against existing rows.

## Test checklist
- Migrations run up and down on a copy of realistic data.
- Concurrent writes to the same row; a retry after a failed transaction.
