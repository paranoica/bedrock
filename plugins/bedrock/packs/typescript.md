# Pack: TypeScript

## Rules
- `strict: true`; no `any` without a comment saying why; no `@ts-ignore` (the code check flags it).
- Validate data at the boundary (request bodies, env, files) with a schema, then trust the type.
- `await` every promise or handle it; no floating promises.
- No `eval`, no `new Function`, no `innerHTML` with outside data.

## Critical zones to consider
Auth middleware, payment flows, database schema and migrations, background jobs.

## Reviewer checklist
- Errors carry a cause and reach a handler; no swallowed `catch {}`.
- Equality with `===`; dates through one library, stored in UTC.
- Bundle size and render cost on frontend changes.

## Test checklist
- Vitest or Jest; fast-check for parsers and calculations.
- `findRelatedTests` / `vitest related` during a task, the full suite at block end.
- Mocks only at the edges (network, clock), never the module under test.
