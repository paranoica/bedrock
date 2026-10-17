# Security precision — context first, exploitability bar, not-a-vulnerability list

Adapted from the ideas of Anthropic's `claude-code-security-review` (github.com/anthropics/
claude-code-security-review): study the repo's own defenses before hunting, report only what
is likely exploitable, and keep a fixed list of things that are not vulnerabilities. Read §1
at the start of Step 5, and §2–§4 at the grounding gate (Step 5c) for every finding whose
category is security.

## §1 Security context first (once per review, before the taint walk)

Find and write down, in working memory, what the repository already relies on:
- auth: middleware, decorators, policy objects, where the session or token is checked;
- input: validation libraries and schemas, where they run (boundary or deep);
- output: the template engine's escaping, the ORM or query builder, the sanitizers in use;
- secrets: how they are loaded (env, vault, files) and whether logs redact them;
- the threat model the code implies: public API, internal tool, CLI, browser-only.

Then compare instead of guessing:
- a new route without the middleware every sibling route has **is** the finding;
- a query built through the project's query builder is not an injection, read it and move on;
- a sanitizer the project uses everywhere is a defense to verify (Step 5's counterfactual),
  not a reason to skip the flow.

## §2 The exploitability bar

A security finding ships only with a named exploit path: who the attacker is, the input they
control, the sink it reaches, and what they gain. Then rate how sure you are that it is
actually exploitable:
- **0.9–1.0** — an exploit path is traced end to end, executed when Step 5d allows: ship;
- **0.8–0.9** — a clear, known exploitation pattern with no defense found on the path: ship;
- **0.7–0.8** — needs specific conditions you could not confirm: at most a *needs
  verification* entry, never CRITICAL or HIGH;
- **below 0.7** — speculation: drop it.

MEDIUM security findings ship only when they are obvious and concrete.

## §3 Not security findings

Do not report these as vulnerabilities. Where the performance or resilience checklist
covers the same effect with real evidence (a measured hot loop, a leak that grows), it
belongs there, under that category.
- denial of service, resource or CPU or memory exhaustion, missing rate limits;
- memory or file-descriptor leaks;
- secrets or credentials stored on disk (managed elsewhere); hard-coded secrets in code
  still are findings;
- outdated third-party dependencies (Step 3's OSV scan owns them);
- missing hardening with no exploit path ("should also set header X");
- theoretical race conditions or timing attacks, unless clearly practical and severe;
- files that only hold tests;
- log spoofing: unsanitized input written to logs;
- user content inside an LLM prompt;
- a crash with no security impact (an undefined value): report it as correctness, if at all;
- memory-safety classes in memory-safe languages (Rust, Go, Python, JS/TS, Java, C#);
- regex denial of service;
- low-impact web classes: open redirect, tabnabbing, XS-Leaks, prototype pollution.

## §4 Precedents

- Environment variables and CLI flags are trusted: an attack that needs to set them is not one.
- UUIDs are unguessable; an attack that needs to guess one is not one.
- React escapes output; XSS in React needs `dangerouslySetInnerHTML` or a similar raw sink.
- Client-side code is not a trust boundary: missing permission checks in browser TS are the
  server's job. SSRF and path traversal in browser-only code are not findings.
- SSRF counts only when the attacker controls the host or the protocol, in server code.
- `../` matters when it reaches a file read, not inside an HTTP request path.
- Command injection in a shell script needs a concrete route for untrusted input to reach it.
- GitHub Actions workflows and notebooks need a very specific, concrete attack path.
- Logging secrets, passwords, request headers or PII is a finding; logging URLs or other
  non-sensitive data is not.
- Missing or editable audit logs are not a vulnerability.
- Injection into a log query is a finding only when it exposes sensitive data to outsiders.
