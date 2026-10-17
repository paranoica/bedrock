# Pack: API security

## Rules
- Every endpoint states who may call it; the check runs on the server, per object, not per route.
- Input validated by a schema; output never echoes internal errors or stack traces.
- Secrets from the environment, never in code, logs or responses.
- Rate limits on login, password reset and anything that sends mail or costs money.

## Critical zones to consider
Auth, permissions, session and token handling, webhooks, file upload.

## Reviewer checklist
- Object-level access: user A cannot read user B's record by changing an id.
- Injection: SQL, shell, path traversal, server-side request forgery on URLs from input.
- Webhook signatures verified; replay windows enforced.
- CORS and cookies: no wildcard with credentials, `HttpOnly`, `Secure`, `SameSite`.

## Test checklist
- One test per role per endpoint touched: allowed and refused.
- Hostile input: huge bodies, odd unicode, wrong types, missing fields.
