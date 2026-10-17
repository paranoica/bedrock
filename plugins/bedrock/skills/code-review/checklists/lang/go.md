# Go — language module

Covers Go (net/http stdlib, Gin, Echo, Fiber, Chi; `database/sql`, GORM, sqlx; cloud-native
codebases). Server-side threat model. Built on `checklists/taint-spine.md` — read that first.
Static helper: `gosec` (G-rules cited below) and `govulncheck` (reachability-aware CVE scan)
— prefer `govulncheck` over a raw OSV match for Go, it filters to *called* vulnerable symbols.

## Sinks by S-category

- **S1 SQL** — `db.Query/Exec/QueryRow` with `fmt.Sprintf`/`+` building the SQL (gosec G201/
  G202). Safe: placeholders (`?` for MySQL, `$1` for pq/pgx) with args. GORM: `.Where("name
  = "+x)` or `.Raw(fmt.Sprintf(...))` is injectable; `.Where("name = ?", x)` is safe. Identifiers
  (table/column/ORDER BY) can't be bound → allowlist.
- **S3 OS command** — `exec.Command("sh","-c", userStr)` / `exec.Command("bash","-c",…)` is the
  command-injection form (gosec G204); `exec.Command("convert", userArg)` (fixed binary, arg
  slice) is the safe form — but still allowlist the binary if its name is tainted, and remember
  some binaries mistreat their own args.
- **S4/S5 Template (SSTI/XSS)** — **`text/template` does NOT auto-escape; `html/template` does.**
  Rendering user data into HTML via `text/template` is XSS. Even with `html/template`,
  `template.HTML(userStr)` / `template.JS` / `template.URL` bypass escaping — treat as S5 sinks.
- **S6 Deserialization** — `encoding/gob` and YAML/`mapstructure` into typed structs are
  generally safe; the live risk is **JSON parser differentials**: Go's `encoding/json` silently
  takes the **last** duplicate key and is case-insensitive on field match — if another service
  in the auth path parses the same body differently, you get an auth-decision split (the 2025
  GitLab SAML-style bypass). Flag when the *same* request body is parsed by two stacks and a
  security decision depends on a field.
- **S7 Path** — `filepath.Join(root, userName)` does NOT stop `../` (Join cleans but still
  escapes root with enough `..`); `http.ServeFile(w,r, r.URL.Path)` is path traversal (gosec
  G305 zip-slip / path). Safe: `filepath.Clean` then verify `strings.HasPrefix(resolved,
  root+string(os.PathSeparator))`, or Go 1.24+ `os.Root`/`root.Open`.
- **S8 SSRF** — `http.Get(userURL)`, any client fetching a tainted URL. Allowlist host+scheme.
  **DNS rebinding bypasses naive validation** (resolve-then-fetch lets the name re-point to
  `169.254.169.254`/private after the check, the 2025 Gotenberg class) — pin the resolved IP
  or use a dialer that re-checks the connected address.
- **S9 Redirect** — `http.Redirect(w,r, r.URL.Query().Get("next"), …)` → open redirect. Allowlist.
- **S11 Format string** — `fmt.Sprintf(userStr, …)` / `fmt.Errorf(userStr)` with user data as
  the *format* (gosec G ... `go vet` printf check) — format must be a constant.
- **S12 IDOR/authz** — handler reads `id := r.PathValue("id")` then loads the row with no owner
  check; trusting a client-sent role/tenant claim.

## Footguns (taint-independent)

- **Range-loop variable capture** — before **Go 1.22**, `for _, v := range xs { go f(&v) }`
  captures one shared `v` (gosec G601 / `loopvar`); a goroutine/closure sees the last value.
  Fixed by per-iteration scoping in 1.22+. **Version-gate this finding by the module's `go`
  directive.**
- **Swallowed errors** — `v, _ := …` on a security-relevant call (auth, decode, write), or a
  `defer f.Close()` whose error is dropped on a *write* path (data loss). A returned `error`
  ignored after a `Write`/`Commit` hides partial failure.
- **`nil` map write / nil-pointer deref** — writing to a nil map panics; dereferencing a nil
  interface/pointer from an unchecked type assertion (`x.(T)` without the `,ok` form) panics →
  DoS on a request path.
- **Goroutine leak** — a goroutine blocked on a channel with no `context` cancellation / no
  receiver leaks for the process lifetime; unbounded `go` per request is a resource bomb.
- **`math/rand` for security** — tokens/IDs/nonces from `math/rand` are predictable; use
  `crypto/rand` (gosec G404).
- **Integer/`int` conversions** — `int(int64Val)` truncation, `len()`-derived sizes cast down;
  unchecked `strconv.Atoi` result used as an index/size.
- **`http.Client` with no `Timeout`** — defaults to no timeout → connection/goroutine pileup
  under a slow upstream (resilience, not just style on a server).

## Sanitizer idioms (what "safe" looks like)

- SQL: parameter placeholders with an args slice, or a query builder that parameterizes.
- HTML: `html/template` with values left to its auto-escaper; never `template.HTML(user)`.
- Path: `os.Root` (1.24+) or Clean+prefix-check against an absolute root.
- SSRF: a custom `net.Dialer.Control` that rejects private/link-local on the *connected* IP.
- Crypto: `crypto/rand`, `subtle.ConstantTimeCompare` for secret/token comparison.

## Framework specifics

- **net/http** — set security headers explicitly (none by default): CSP, `X-Content-Type-
  Options: nosniff`, frame options. `http.ServeMux` `PathValue` is unvalidated input.
- **Gin / Echo / Fiber** — `c.Query/Param/FormValue` are tainted sources; binding (`c.Bind`/
  `ShouldBindJSON`) does not validate beyond types unless `binding:` tags are set — missing
  validation tags on a bound struct is a gap. Echo's `c.Redirect`/Gin static file serving →
  the S7/S9 sinks above.
- **GORM** — `.Raw`/`.Exec`/string `.Where` are the injectable surface; struct-based and
  `?`-arg queries are safe. `.Updates(map)`/binding a whole request struct → mass assignment.

## Version & severity notes

- Memory-class issues are rare in pure Go (GC, no manual frees) — the exception is **`cgo`**
  and `unsafe`, which reintroduce the C module's S10 (e.g. the 2026 cgo `LookupCNAME`
  double-free class). Review `unsafe`/`cgo` blocks with the C module open.
- Run `govulncheck ./...` — it reports only CVEs whose vulnerable symbol is actually reachable,
  cutting the OSV false-positive rate sharply. Treat its reachable hits as CRITICAL/HIGH.
- Severity per `references/severity-rubric.md`: injection sinks with a confirmed tainted flow →
  CRITICAL/HIGH; swallowed-error/goroutine-leak → MEDIUM unless on a money/auth path.
