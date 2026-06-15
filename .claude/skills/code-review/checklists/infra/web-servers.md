# Web servers (Nginx / Apache / Caddy) — misconfig checklist

Covers reverse-proxy and static-serving config. Web-server misconfig causes path traversal,
SSRF, request smuggling, and information disclosure independent of app code. Built on the
spine's misconfig stance. Static helpers: `gixy` (nginx), `nginxpwner`, `apachetomcatscanner`,
config linters.

## Nginx

- **`alias` path traversal / off-by-slash (the classic, Orange Tsai "Breaking Parser Logic!").**
  A `location /files {` (no trailing slash) with `alias /data/files/;` lets `/files../etc/passwd`
  escape the directory. The same off-by-slash bites **`proxy_pass`**:
  `location /api { proxy_pass http://apiserver/v1/; }` turns `/api../secret` into a path the
  backend resolves above `/v1/`. Match trailing slashes between `location` and `alias`/`proxy_pass`,
  or use `root`. Flag mismatched-slash blocks.
- **`proxy_pass` SSRF / open proxy.** `proxy_pass` to a URL built from a variable that includes
  client input (`$uri`, `$document_uri`, `$arg_*`, `$http_*`) → SSRF/routing to internal hosts;
  a `resolver` + variable `proxy_pass` can be steered (to `/etc/passwd` files or cloud metadata).
  **Use `$request_uri`, not `$uri`/`$document_uri`** (the latter are decoded/normalized and are
  the injectable ones). Pin upstreams; never proxy to a client-controlled host.
- **CRLF / response splitting via `$uri`.** Because `$uri` decodes URL-encoded `%0d%0a`, using it
  in `add_header`/`return`/`rewrite` lets an attacker inject new response headers (session
  fixation, cache poisoning). Use `$request_uri` and don't reflect decoded path into headers.
- **h2c smuggling.** If nginx passes `Upgrade`/`Connection` headers to the backend, an attacker
  can upgrade to cleartext HTTP/2 and tunnel directly to the `proxy_pass` backend, bypassing
  nginx's path/ACL checks (any path on that internal endpoint becomes reachable). Don't forward
  Upgrade/Connection unless WebSockets are intended.
- **SNI-proxy SSRF (stream module).** `proxy_pass $ssl_preread_server_name:443;` uses the
  client-supplied SNI directly as the backend address → connect to any internal host by setting
  SNI. Allowlist backends; don't route on raw SNI.
- **`merge_slashes off` / normalization gaps** → ACL bypass (`//admin`, `/./`, encoded
  traversal reaching a path that a prefix check thought it blocked).
- **`add_header` inheritance trap** — defining any `add_header` in a `location` **drops all
  inherited headers** from the parent (so security headers/HSTS/CSP silently vanish in that
  location). Re-declare or use `always`.
- **Exposed sensitive paths** — `.git/`, `.env`, `.htpasswd`, backups, `autoindex on` listing
  directories, `/server-status`/stub_status open. Deny dotfiles and metadata paths.
- **Request smuggling** — inconsistent handling of `Content-Length`/`Transfer-Encoding` between
  nginx and the upstream; old versions / misconfigured `proxy_http_version`.
- **OpenResty/`ngx_lua`** — `content_by_lua*` building Lua from request data, or `os.execute`
  in Lua → see `checklists/infra/redis.md` Lua notes (same sandbox concerns).

## Apache (httpd)

- **`.htaccess`/`AllowOverride All`** enabling unexpected directives; `Options +Includes`
  (SSI injection), `+ExecCGI`, `Indexes` (dir listing), `FollowSymLinks` traversal.
- **`mod_proxy` open/SSRF** — `ProxyPass` to client-influenced targets; `ProxyRequests On`
  (forward-proxy = open proxy).
- **`RewriteRule` flaws** — passing user input into a proxy/`P` flag target; `mod_cgi` with
  user-influenced scripts (Shellshock-era env passing).
- **Exposed** — `server-status`/`server-info` public; default pages; verbose `ServerTokens`/
  `ServerSignature` leaking version.

## Caddy

- Generally secure-by-default (auto-HTTPS), but watch: the **`templates` directive reflecting a
  request value → file read / SSTI**, e.g. `respond "You came from {http.request.header.Referer}"`
  with `templates` enabled lets `Referer: {{readFile "etc/passwd"}}` read host files (Go template
  execution on attacker input); `reverse_proxy` to a dynamic/client-influenced upstream (SSRF);
  `file_server` with `browse` (dir listing); overly broad matchers exposing internal routes;
  admin API (`localhost:2019`) bound non-locally.

## Cross-cutting

- **Missing security headers** — HSTS, CSP, `X-Content-Type-Options: nosniff`, frame options,
  `Referrer-Policy` (defense-in-depth; flag absence on an HTML app, mind the nginx inheritance
  trap above).
- **TLS** — old protocols/ciphers (TLS 1.0/1.1, RC3/CBC), missing OCSP stapling, wildcard certs
  over-shared; HTTP not redirected to HTTPS.
- **Rate limiting / body size** — no `limit_req`/`client_max_body_size` → DoS / large-upload abuse.

## Current CVE / version notes (keep the server patched, not just configured)

- **nginx** — HTTP/3 (QUIC) stack overflow / UAF / NULL-deref (CVE-2024-31079 / 32760 / 35200,
  fixed 1.27.0+ / 1.26.1+); SSL session-reuse vuln (CVE-2025-23419, fixed 1.27.4+ / 1.26.3+);
  mp4 module overread (CVE-2024-7347); SMTP overread (CVE-2025-53859, fixed 1.29.1+). **HTTP/2
  Rapid Reset (CVE-2023-44487)** still bites nginx when `keepalive_requests`/HTTP-2 limits are
  cranked → DoS. Record the version and gate findings on it.
- **Apache httpd** — `mod_proxy` `ProxyPass` + rewrite → **HTTP request smuggling**
  (CVE-2024-40725) and `mod_ssl` `SSLVerifyClient` **auth bypass** (CVE-2024-40898) in
  2.4.0–2.4.61 (~7.6M instances exposed, PoCs public). Confirm the build is past these.
- Version-gate every engine CVE against the deployed version and how you confirmed it; landing
  per `references/severity-rubric.md`.

## What "safe" looks like

- `alias`/`root` with matched slashes; pinned upstreams (no client-controlled `proxy_pass`);
  normalization on; dotfiles/metadata/status endpoints denied; headers re-declared with `always`.
- Apache: least `AllowOverride`, no `ProxyRequests On`, status pages restricted, tokens minimal.
- Modern TLS only with HTTP→HTTPS redirect; security headers present; request size + rate limits set.

Cross-refs: SSRF mechanics → `checklists/taint-spine.md` (S8); upstream app → its language module;
Lua → `checklists/infra/redis.md`.
