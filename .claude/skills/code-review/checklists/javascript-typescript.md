# JavaScript / TypeScript Checklist

Stack-specific issues for Node, Next.js, React, and the broader JS ecosystem.

## Node.js / Server-side

### Async / Promise handling
- `await` inside `forEach` doesn't actually await — use `for...of` or `Promise.all` with `map`
- Unhandled promise rejections — every async function called without await needs `.catch` or void marker
- Missing `try/catch` around `await` in async handlers — Express middlewares need `next(err)` or async wrappers
- Mixing callbacks and promises in the same flow — pick one

### Event loop
- CPU-bound work in handlers (heavy crypto, big JSON parse on >MB payloads, image processing) → blocks all requests. Move to worker_threads or external service.
- `JSON.parse` of attacker-controlled large payload — body size limits at the framework layer (`express.json({ limit: '100kb' })`).

### Express / Fastify gotchas
- `app.use(express.json())` with no limit — default 100kb, but check.
- `app.use(cors())` with no config — allows everything. Pin origins.
- `req.params` / `req.query` used as object keys without sanitization → prototype pollution potential.
- Error-handling middleware that returns stack traces in prod.

### Next.js specifics
- **Server Actions:** must validate auth & input inside the action — they're public endpoints whether you like it or not. Treat them like API routes.
- **API routes** (`pages/api/`, `app/api/`): same — they're public. Never assume "only my frontend calls this."
- **Route handlers** reading `cookies()` for auth — make sure session validation actually runs.
- **`use client` boundary leaks:** importing server-only code into a client component leaks it to the bundle. Use `import "server-only"`.
- **`process.env.NEXT_PUBLIC_*`** is shipped to the browser. Anything sensitive here = secret leak.
- **Middleware** running on every request: don't do heavy work there, don't do DB calls. It's edge runtime in most setups.
- **`revalidatePath` / `revalidateTag`:** ensure you call them after mutations or cached data goes stale.
- **Image domains** in next.config.js — wildcard `**` = SSRF-style risk via image optimization endpoint.

### React (where it overlaps with security/perf)
- `dangerouslySetInnerHTML` — every occurrence audited
- `href={userControlledUrl}` without `javascript:` filter → XSS
- `useEffect` with empty deps doing auth checks — runs once on mount, won't re-check on token change
- Storing JWT/session in localStorage — XSS-stealable (see security-general.md)
- Server components passing secrets through props to client components

### TypeScript-specific
- `any` in security-sensitive paths (auth, input validation) — defeats the type system precisely where you need it
- `as` casts on untrusted input — `req.body as User` is a lie, validate with zod/io-ts
- `// @ts-ignore` / `// @ts-expect-error` near security boundaries — investigate
- `unknown` cast to specific type without runtime check — same problem
- Disabled strict null checks → null deref bugs

## Package / supply chain

- `package.json` `scripts` running `curl | sh` or downloading at install — backdoor vector
- `postinstall` scripts in dependencies — supply chain risk
- Direct dependencies on packages with very recent first publish + few weekly downloads — possible typosquat
- Pinned vs ranged versions: `^` and `~` allow auto-updates; for security-sensitive deps prefer exact pins + Renovate/Dependabot

## Common bad patterns

```javascript
// Race condition: check-then-act
if (!await User.findOne({ email })) {
  await User.create({ email })  // two requests can both pass the check
}
// Fix: unique constraint + handle conflict

// Async in array methods that don't await
items.forEach(async (i) => { await save(i) })  // returns immediately
// Fix: for...of, or Promise.all(items.map(save))

// Implicit type coercion in comparisons
if (req.query.admin == true) { ... }  // "false" == true is false, but "1" == true is true. Use ===

// Object spread on user input
const updated = { ...user, ...req.body }  // mass assignment, user can override role/id
// Fix: explicit field allowlist

// catch (e) and continue without logging
try { ... } catch (e) {}  // silent failure — flag

// Date math without timezone
new Date(userDate)  // depends on server TZ. Be explicit with UTC or libraries.
```

## Frontend XSS-adjacent

- URL building with user input inserted directly into `href`/`src` — at minimum strip `javascript:` and `data:`
- `target="_blank"` without `rel="noopener noreferrer"` — reverse tabnabbing (low severity, but easy fix)
- Open redirects via `router.push(req.query.next)` — validate the destination
- iframes with user-controlled `src` — sandbox attribute
