# General Security Checklist

Run alongside the injection checklist. Covers auth, crypto, secrets, authorization, and the rest of OWASP.

## 1. Authentication

- **Password storage:** bcrypt (cost ≥ 12), argon2id, or scrypt. NEVER md5/sha1/sha256 alone, NEVER plaintext. Flag any custom hashing.
- **Password comparison:** constant-time only. `bcrypt.compare`, `hmac.compare_digest`. Never `==` on raw hashes.
- **Session tokens:** generated from CSPRNG (`crypto.randomBytes`, `secrets.token_urlsafe`). Never `Math.random()`, never timestamps, never user-controlled.
- **JWT:**
  - Algorithm pinned server-side, not read from JWT header. `alg: none` and algorithm confusion attacks are still common.
  - HS256 secret must be strong (≥32 bytes random). Flag short or default secrets.
  - RS256: verify the public key isn't being substituted via `kid` injection.
  - **Always validate `exp`, `nbf`, `iss`, `aud`.** Missing any = HIGH.
  - **Disabling built-in checks is a red flag.** `options={"verify_exp": False}`, `{ignoreExpiration: true}`, `verify=False` — flag every occurrence. The reason given is almost always wrong.
  - JWTs in localStorage = XSS-stealable. Flag and recommend httpOnly cookie.
- **MFA:** if the app has it, verify it's enforced server-side, not just hidden client-side. Verify TOTP code reuse is blocked (replay protection).
- **Account enumeration:** "user not found" vs "wrong password" responses leak account existence. Same with timing.

## 2. Authorization (the bigger silent killer)

This is where most production breaches actually live. Always check:

- **IDOR:** Every route that takes an ID — verify it checks the ID belongs to the current user/tenant. `GET /api/orders/:id` without an ownership check is **CRITICAL** if orders contain anything sensitive.
- **Mass assignment / over-posting:** `User.update(req.body)` lets the user set `is_admin: true`. Flag every model update that blindly spreads request data.
- **Privilege escalation paths:** look for `role`, `is_admin`, `is_staff`, `permissions` being writable from user-facing endpoints.
- **Tenant isolation:** in multi-tenant apps, every query must scope by tenant. Look for queries missing the tenant_id filter.
- **Permission checks at the wrong layer:** UI hides admin buttons but API doesn't check. Always check at API/service layer.
- **Insecure direct object references in URLs:** sequential IDs (`/invoice/1234`) make IDOR enumeration easy — flag if combined with weak auth.

## 3. Secrets

- **Hardcoded secrets:** API keys, tokens, passwords, private keys in source. gitleaks will catch most; manually verify the rest. Even test secrets in source are bad (real ones leak through copy-paste).
- **Secrets in logs:** look for `console.log(req)`, `print(request)`, `logger.info(user)` — these often spray tokens/passwords/PII.
- **Secrets in error messages:** stack traces returned to the client that include connection strings, file paths, internal URLs.
- **Secrets in client bundles:** anything in `process.env.NEXT_PUBLIC_*`, `REACT_APP_*`, `VITE_*` is shipped to the browser. Verify nothing sensitive lives there.
- **Default credentials:** `admin/admin`, `root/root`, dev seed users with weak passwords reachable in prod.

## 4. Cryptography

- **Algorithm choices:** AES-GCM, ChaCha20-Poly1305 for sym encryption. RSA-OAEP / Ed25519 / ECDSA-P256 for asym. Flag DES, 3DES, RC4, ECB mode, MD5, SHA1.
- **IV/Nonce reuse:** AES-GCM nonce reuse with the same key = catastrophic. Each encryption must use a fresh random nonce.
- **CBC mode:** padding oracle risk. Prefer GCM.
- **Custom crypto:** any hand-rolled "encryption" — flag immediately and demand a standard library.
- **TLS:** verify cert validation isn't disabled (`rejectUnauthorized: false`, `verify=False`, `InsecureSkipVerify: true`).

## 5. CSRF

- For cookie-based session apps: every state-changing endpoint needs CSRF protection (SameSite=Strict/Lax cookie, anti-CSRF token, or origin check).
- For pure token-auth APIs (Bearer in header): CSRF mostly N/A, but verify no fallback to cookies.

## 6. Rate limiting & abuse

- Auth endpoints (login, signup, password reset) — rate limit by IP and account. Missing = HIGH.
- Expensive endpoints — search, AI calls, file generation — rate limit by user. Missing = MEDIUM-HIGH depending on cost.
- Password reset tokens — single use, short expiry, sufficient entropy.

## 7. Input validation

- Schema validation at the boundary (zod, pydantic, joi, Marshmallow). Reject unknown fields. Type-check everything.
- Length limits on every string field that hits storage or display. Unbounded → memory DOS.
- Numeric ranges enforced. Especially negative numbers where positive expected.

## 8. CORS

- `Access-Control-Allow-Origin: *` combined with `Allow-Credentials: true` = forbidden by spec but some custom middleware does it. Critical leak.
- Origin reflection without an allowlist: `Allow-Origin: <whatever request had>` is the same as `*`.

## 9. File uploads

- Verify content type by content, not just by header/extension (magic bytes).
- Store outside webroot, serve via authenticated handler that sets `Content-Disposition: attachment` for risky types.
- Strip EXIF from images that get re-served (privacy leak).
- Size limits enforced server-side.
- Filename: never trust user-supplied. Generate UUID, store original name separately.
- Image processing libraries: ImageMagick, Pillow have had RCE CVEs — check versions against OSV.

## 10. Logging & monitoring

- PII in logs (emails, phone numbers, SSN-equivalents, payment data) — flag.
- Auth failures NOT logged — flag (you want this for incident response).
- Stack traces returned to client in prod — flag.

## 11. Dependency hygiene

- Lockfile present (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, etc.) — if missing, flag MEDIUM (non-reproducible builds, hard to audit).
- `npm audit`/`pip-audit` findings if Step 3 surfaced them.
- Unmaintained packages (last release > 2 years ago for security-sensitive deps).

## 12. Server config / headers

- Security headers: CSP, HSTS, X-Content-Type-Options, X-Frame-Options / frame-ancestors, Referrer-Policy. Missing — usually MEDIUM unless the app is high-value.
- Cookies: `Secure`, `HttpOnly`, `SameSite` set on session cookies.
- DEBUG=True in Django/Flask in prod paths — CRITICAL if reachable.
- Detailed error pages in prod — MEDIUM.

## 13. Insecure Design (OWASP A04)

This is fuzzier than "is this line buggy" — it's about architectural mistakes. Look for:
- **No rate limit on expensive or sensitive operations** — covered in §6, but specifically: password reset emails (spam attack), payment retries, AI generation costs.
- **No idempotency on payment/order flows** — duplicate charges on network retry.
- **Trust boundaries violated in design** — frontend "validation" is treated as the only check, with no server-side equivalent.
- **Hardcoded business limits** — `if user.balance > 1_000_000: alert_admin()` — flag values that should be config.
- **No tenant isolation in design** — multi-tenant systems where the design assumes single tenant and security depends on every developer remembering to filter by tenant_id.
- **Missing recovery / lockout policy** — what happens when a user is compromised? Can sessions be revoked? Are session tokens stateless JWTs with no revocation mechanism?
- **Logging that can't drive incident response** — no record of auth events, no record of authz decisions, no PII access trail. (Yes, the inverse of "PII in logs" — sometimes the problem is too little.)

These are usually **MEDIUM** or **HIGH** with note "design concern, not exploit-now".

## 14. Software & Data Integrity (OWASP A08)

- **Unverified dependency sources:** `pip install` from non-PyPI URLs in CI, `npm install` with `--registry` pointing to internal mirrors that aren't pinned.
- **Auto-update of dependencies:** ranges like `^x.y.z` allow silent minor updates including malicious takeover versions. Demand exact pinning + Renovate/Dependabot for security-sensitive deps.
- **Unsigned package consumption:** no SLSA verification, no checksum pinning.
- **CI/CD secrets exposed to PR builds from forks** — classic supply chain attack vector. GitHub Actions defaults are okay; check workflow `pull_request_target` usage.
- **Deserialization of trusted-source data** is still risky if "trusted source" can be compromised. Don't pickle from anywhere, ever — see injection-deep §7.
- **Build artifacts not reproducible** — if you can't reproduce a build, you can't verify it wasn't tampered with.
- **Insecure update mechanisms** — auto-updaters that don't verify signatures.


## How to write findings

Use the format from `references/report-template.md`. Always include the OWASP category if applicable (A01:2021 Broken Access Control, etc.) — it gives the user a concrete reference.
