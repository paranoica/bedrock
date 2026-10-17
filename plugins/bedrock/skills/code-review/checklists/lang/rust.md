# Rust — language module

Covers Rust (Axum, Actix, Rocket, warp; sqlx/Diesel/SeaORM; CLI/systems). Server-side threat
model. Built on `checklists/taint-spine.md`. The headline: **memory-safe ≠ secure.** Rust
removes most of C's S10 in *safe* code, but panics, `unsafe`, integer overflow, and ordinary
logic bugs remain. Static helpers: `cargo audit` (RustSec advisory DB), `cargo geiger`
(unsafe usage count), `clippy` (`-W clippy::pedantic`), **Miri** (UB in `unsafe`/FFI).

## The two Rust-specific axes

- **S13 Panic = DoS (the most under-rated Rust finding).** `.unwrap()`, `.expect()`, direct
  slice/array indexing `a[i]`, `[a..b]` range slicing, integer division/`%` by zero, and
  `.unwrap()` on a `Mutex` lock (poisoning) all **panic** on bad input → thread/handler abort,
  often the whole service. (A single production `.unwrap()` took Cloudflare down across 330+
  data centers on 2025-11-18.) On any request/parse path flag `unwrap`/`expect`/`[idx]`/
  unchecked division on data that can be attacker-influenced; require `match`/`?`/`.get()`/
  `checked_*` / a `catch_unwind` boundary instead.
- **S10 `unsafe` reintroduces C's memory bugs.** Inside `unsafe { }`: raw-pointer deref (UAF,
  null, OOB), `transmute` (type confusion), `slice::from_raw_parts` with a wrong length,
  `get_unchecked`, `set_len` before init, and **FFI** (`extern "C"`) where C return values and
  buffers are trusted. Read every `unsafe` block with `checklists/lang/c.md` open; check the
  *soundness* invariant it must uphold. Miri is the receipt.

## Integer overflow (version/profile-sensitive)

`a + b`, `a * b` on sizes/indices **panic in debug but silently WRAP in release** unless
`overflow-checks = true` is set in the release profile. A wrapped length/index then drives a
logic bug or feeds a `get_unchecked`. Flag arithmetic on input-derived sizes that doesn't use
`checked_add`/`checked_mul`/`saturating_*`/`Wrapping`; note whether the project sets
`overflow-checks`.

## Injection sinks (still present)

- **S1 SQL** — `sqlx::query(&format!("... {x}"))` / Diesel `sql_query(format!(...))` with
  interpolation. Safe: sqlx bind args (`query!("... ?", x)` / `.bind(x)`; the `query!` macro is
  compile-time checked) and Diesel's typed DSL.
- **S3 Command** — `Command::new("sh").arg("-c").arg(user)` → injection; use a fixed program +
  arg list, no shell.
- **S6 Deserialization / parsing** — serde into untrusted input is generally safe (binds to a
  concrete type), but watch unbounded allocation from a length field, `serde_json` recursion
  depth (stack-overflow DoS), and crates with RUSTSEC bound-check advisories.
- **S8 SSRF** — `reqwest`/`hyper` client to a tainted URL (allowlist, block metadata/private).

## Footguns (taint-independent)

- **Ignored `Result`/`#[must_use]`** — `let _ = result;` swallowing an error on a security/write
  path; `.ok()` discarding a failure.
- **Lock poisoning / deadlock** — `.lock().unwrap()` panics if a holder panicked; holding two
  locks in inconsistent order; holding a lock across an `.await` (Tokio) → deadlock/stall.
- **Blocking in async** — a blocking call (`std::fs`, heavy CPU) on a Tokio worker starves the
  runtime → latency/DoS; use `spawn_blocking`.
- **`mem::transmute` / as-casts** — lossy `as` conversions (`u64 as u32` truncation) on sizes.

## Sanitizer idioms (what "safe" looks like)

- No `unwrap`/`expect`/raw-index on request paths — `?`, `match`, `.get()`, `checked_*`.
- `unsafe` minimized, each block documented with its soundness invariant, Miri-tested.
- `overflow-checks = true` in release, or explicit `checked_*`/`saturating_*` on input math.
- sqlx `query!`/bind params; fixed-arg `Command`; bounded deserialization.

## Framework specifics

- **Axum/Actix** — extractors (`Json`, `Query`, `Path`, `Form`) are tainted input; a handler
  returning `Result<_, E>` where `E` doesn't map untrusted errors to a generic response can leak
  internals; missing auth middleware/extractor on a route; CORS set to permissive.
- **Severity** per `references/severity-rubric.md`: `unsafe` memory bug reachable from input →
  CRITICAL/HIGH; panic-DoS on a request path → HIGH/MEDIUM by blast radius; release-overflow →
  MEDIUM unless it feeds an unsafe index.
