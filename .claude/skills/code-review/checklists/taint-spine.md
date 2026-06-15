# Taint-Spine — the language-agnostic core

Read this before the LLM review sweep, then load the thin per-language module(s) for the
detected stack (`index.json` → `stack_routes`). The spine holds the *reasoning*; the
language module holds that language's *concrete sinks, footguns, and sanitizer idioms*.
Any language without a module is still reviewed through this spine — say "spine-only
coverage, no language-specific module" in the report header.

## The one rule

**A finding = a tainted source reaches an unsafe sink in the same flow.**

Both halves are required. No tainted source (value is hardcoded, constant, or derived only
from trusted config) → not a finding. Provably-safe sink (parameterized query, schema-
validated parse, allowlist, sandbox, fixed-arg exec) → not a finding. If either half is
unproven, it stays a `needs verification` finding with the exact check — never a silent drop
and never a fabricated CRITICAL.

## Step 1 — Enumerate sources (what is tainted)

Untrusted input, by decreasing obviousness:
- **Direct request data:** body, query string, path params, headers (incl. `Host`,
  `X-Forwarded-*`, `Referer`, `User-Agent`), cookies, multipart/file uploads.
- **Indirect / second-order:** values previously stored from user input (DB rows, cache),
  queue/topic messages, WebSocket frames, webhook payloads, third-party API responses.
- **Credential-shaped but still attacker-controlled:** JWT claims **after** signature
  verification (the payload is whatever the attacker put there — verification proves
  integrity, not safety of the values), OAuth profile fields, SAML attributes.
- **Environment-as-input:** env vars / config that are themselves set from user-facing
  forms, filenames, or tenant data; CLI args on a tool that runs untrusted input.
- **Filesystem/network reflections:** contents of an uploaded archive, an SVG, a parsed
  document, a redirected URL's response.

Default stance: **treat as tainted until proven otherwise.** "Surely the caller validates
this" is an assumption to confirm by reading the caller, not a reason to untaint.

## Step 2 — Trace the flow (across boundaries)

For each source, follow the value through assignments, function calls, and returns to every
sink it can reach. Taint propagates through: concatenation, formatting/interpolation,
collection membership, struct/object fields, and most "transform" helpers. Taint is only
*cleared* by a sanitizer you have **read and confirmed** clears it for that sink (Step 4).

When the flow leaves the current file, resolve the callee — `scripts/build_index.py <root>
--defs <name>` for its definition, `--callers <name>` for blast radius — and read the real
body. Do not assume what a cross-file callee does. Stopping at the first file is the #1
cause of missed bugs for diff-only reviewers.

## Step 3 — Sink categories (the universal taxonomy)

Every dangerous operation falls into one of these. The thin language module names the
concrete functions/constructs for each; here is what to *look for* and the safe form.

| # | Sink category | What goes wrong | Safe form |
|---|---|---|---|
| S1 | **SQL / query language** | tainted value built into query text | parameter binding; allowlist for identifiers (table/column/ORDER BY can't be bound) |
| S2 | **NoSQL / ORM operator** | tainted object becomes a query operator (`{$gt:""}`), or raw-query escape hatch | schema-validate to a scalar before query; never pass raw request objects as filters |
| S3 | **OS command / process** | tainted string parsed by a shell | fixed-arg exec (array, `shell=false`); allowlist the binary and args |
| S4 | **Code / template eval** | tainted string executed as code or markup | never eval user input; auto-escaping template context; no `\|safe`/`{{{...}}}`/`mark_safe` on tainted data |
| S5 | **HTML / DOM output (XSS)** | tainted value rendered without context-correct escaping | framework escaping; sanitizer (DOMPurify) for rich HTML; CSP as defense-in-depth |
| S6 | **Deserialization** | tainted bytes reconstructed into objects/gadgets | safe/whitelisted formats only (no native `pickle`/`unserialize`/`BinaryFormatter`/Java `ObjectInputStream`/`yaml.load` on untrusted input) |
| S7 | **Path / filename** | `../` or absolute path escapes the intended dir | canonicalize then verify the resolved path stays under the allowed root; never trust the supplied name |
| S8 | **Outbound request (SSRF)** | tainted URL/host fetched by the server | allowlist host/scheme; block link-local/metadata (`169.254.169.254`), private ranges, redirects-to-internal; resolve-then-check |
| S9 | **Redirect / forward** | tainted `next`/`returnUrl` causes open redirect | allowlist relative paths or known hosts; reject `//`, scheme-relative, absolute external |
| S10 | **Memory operation** | tainted length/index/pointer drives a copy/alloc/access | bounds-checked APIs, size validation, no raw `strcpy`/unchecked index (see C/C++/unsafe-Rust modules) |
| S11 | **Format string** | tainted value used as the format, not an arg | format is always a constant literal; user data is an argument |
| S12 | **Authn/Authz decision** | tainted value drives an access decision unchecked | server-side ownership/permission check on every object access (IDOR); never trust client-supplied role/id |
| S13 | **Regex / parser (DoS)** | tainted input drives catastrophic backtracking or unbounded work | linear-time engines or input caps; bounded recursion/size on parsers |

## Step 4 — Verify the defense, don't assume it

A call named `validate()`, `is_safe()`, `sanitize()`, `clean()`, `escape()` proves nothing
until you read its body and prove it stops the sink-specific attack:
- **Construct the worst input.** For S1 a quote/comment payload; S5 an event-handler or
  `javascript:` URL; S7 `..%2f` and absolute paths; S8 `//metadata`, a decimal-IP, a
  DNS-rebind, a redirect; S3 `;`/`$()`/backtick/newline.
- **Trace whether the defense rejects that exact input.** Common failures: unanchored regex,
  blocklist instead of allowlist, validation on a *different* field than the one that reaches
  the sink, canonicalization done *after* the check, escaping for the wrong context (HTML-
  escape applied to a JS or URL context), TOCTOU between check and use.
- A defense that provably catches your worst input earns the "safe" call. A defense you only
  *named* does not.

## Step 5 — Sanitizer/sink mismatch (the subtle class)

Even when a sanitizer exists, it can be the wrong one for the sink: HTML-escaping a value
that lands in a SQL string, URL-encoding a value used in a shell, `escapeHtml` on an
attribute without quoting, JSON-stringify treated as injection-safe for HTML. Match the
escaper to the **sink's** grammar, not to where the data came from.

## What the thin language module must provide

(See `checklists/lang/CONTRACT.md`.) For its language: the concrete **sinks** per S-category
above, the **footgun list** (language traps that cause bugs independent of taint — e.g.
integer overflow, mutable defaults, `==` type juggling), the **sanitizer idioms** (the
*correct* safe form a reviewer should expect to see), and **framework specifics** for the
common web frameworks. Keep it thin — the flow reasoning is here, not repeated there.
