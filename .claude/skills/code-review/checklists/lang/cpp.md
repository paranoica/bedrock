# C++ — language module (delta over `c.md`)

C++ inherits **all** of `checklists/lang/c.md` (raw pointers, buffers, format strings, integer
issues, the S10 sweep, hardening flags, ASan/UBSan). Read that first; this file is the C++-only
delta. Modern C++ (RAII, smart pointers, `std::` containers) *reduces* the C surface but adds
its own corruption and lifetime traps. Threat model and severity are the same: memory
corruption → CRITICAL/HIGH.

## Lifetime & ownership traps (the dominant modern class)

- **Dangling references/views.** A reference, pointer, `string_view`, or `span` outliving the
  object it points into — e.g. returning `string_view` to a local `std::string`, or binding a
  `const&` to a temporary that's destroyed at the end of the full expression. `string_view`
  over a temporary `std::string` (`sv = (s1 + s2)`) dangles immediately.
- **Iterator/reference invalidation.** Holding an iterator, pointer, or reference into a
  `vector`/`string`/`unordered_map` across an operation that reallocates or rehashes
  (`push_back`, `insert`, `erase`, `reserve` growth) → UAF. Flag a stored iterator used after a
  mutating call.
- **Smart-pointer misuse.** `shared_ptr` cycles → leak (use `weak_ptr` for back-edges); building
  two `shared_ptr` from the *same raw pointer* → double-free; `.get()` stored and used after the
  owner is destroyed; `unique_ptr` moved-from then dereferenced.
- **Use-after-move.** Reading a moved-from object beyond a valid-but-unspecified state, or moving
  an object still aliased elsewhere.

## Bounds & conversion (C++ flavors)

- **`operator[]` does not bounds-check** on `vector`/`array`/`string` (`.at()` does). OOB via
  `[]` with an input-derived index is the same heap/stack corruption as C.
- **`reinterpret_cast` / C-style cast / `union` type-punning** → type confusion; `static_cast`
  down a wrong hierarchy → UB. `c_str()`/`data()` lifetime tied to the owning string.
- **Narrowing** in `{}`-init is an error, but `()`-init and assignment still narrow silently.

## Exceptions, errors, concurrency

- **Exception safety / partial state.** A throw between two mutations that should be atomic
  leaves an invariant broken; a destructor that throws → `std::terminate`. Check noexcept
  contracts on move ops used by containers.
- **Swallowed errors.** `catch(...){}` that hides failures on a security/IO path; ignoring a
  `std::error_code` overload's result.
- **Data races** (also `concurrency-and-data-integrity.md`): shared mutable state across threads
  with no synchronization is UB in C++, not just a logic bug — `std::atomic`/mutex required;
  `std::shared_ptr` control block is thread-safe but the *pointee* is not.

## Injection sinks still present

S1 SQL (string-built queries to libpq/MySQL connector → bind instead), S3 `system`/`popen`,
S6 deserialization of untrusted data into objects via hand-rolled or library readers, S8 SSRF
in any HTTP client. The taint-spine applies unchanged.

## Sanitizer idioms (what "safe" looks like)

- Ownership expressed through `unique_ptr`/`shared_ptr`/value semantics, not raw `new`/`delete`.
- Container access via `.at()` or a checked index on hot/input paths; no stored iterator across
  a mutating op.
- `string_view`/`span` only over storage that provably outlives them.
- RAII for every resource (lock_guard, file/socket wrappers); no naked `new` paired with manual
  `delete`.
- Built and tested under ASan + UBSan; `-Wall -Wextra -Werror` clean.
