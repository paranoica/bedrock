# Frontend Safety

## Principle

The frontend is never the security boundary — the backend is the source of truth. Frontend safety is hygiene, not defense.

## Hygiene checklist

- **XSS** — avoid `dangerouslySetInnerHTML`; if unavoidable, sanitize.
- **No secrets in the client** — no API keys, no credentials in frontend code.
- `rel="noopener"` on external links.
- **Tokens not in `localStorage`** — use safer storage for auth tokens.
- Set `CSP` and `X-Frame-Options`.
- Form validation on the client is for UX; it is **always duplicated on the server**.
- Audit dependencies.
- Errors shown to the user are generic — no stack traces, no internal detail.

## Framing

All of the above is stated at the level of principle, not a specific stack. The project's `CLAUDE.md` carries stack-specific specifics.

## Status

- The entire hygiene checklist: **MUSTHAVE-BASE**.
