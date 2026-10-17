# C — language module

Covers C (C99–C23), systems/embedded/native extension code. The threat model is dominated
by **memory safety** (S10), the axis no other module in this skill carries. Built on
`checklists/taint-spine.md`. Static helpers: `clang --analyze` / Clang Static Analyzer,
`cppcheck`, `-Wall -Wextra -Werror`; dynamic: ASan + UBSan (`-fsanitize=address,undefined`),
MSan for uninitialized reads, Valgrind. Hardening flags whose *absence* is itself a finding
on a security-sensitive binary: `-fstack-protector-strong`, `_FORTIFY_SOURCE=2/3`, PIE/ASLR,
RELRO, CFI.

Memory-corruption findings are **CRITICAL/HIGH by default** — they are the root cause of RCE,
privilege escalation, and full compromise (UAF, heap-overflow, OOB-write top the CWE KEV list).

## S10 — Memory operations (the core sweep)

For every buffer/pointer/length that touches input, ask: *is the size checked, is the lifetime
valid, is the index in range?*

- **Spatial: buffer overflow / OOB read-write.**
  - Unbounded copies: `strcpy`, `strcat`, `sprintf`, `gets` (removed in C11 — flag any use),
    `scanf("%s", …)` with no width. Bounded-but-misused: `strncpy` does **not** NUL-terminate
    on truncation; `strncat`'s size arg is *remaining space*, not total; `snprintf` truncates
    silently (check the return). Safe: explicit length checks, `strlcpy`/`strlcat` where
    available, always reserve room for the NUL.
  - Arithmetic on sizes: `malloc(n * size)` where `n*size` overflows → undersized allocation
    → heap overflow on write. Use overflow-checked multiply / `calloc`. `len - 1` when `len`
    can be 0 underflows to `SIZE_MAX`.
  - Index/length from input used without a range check before `arr[i]` / `memcpy(dst, src, len)`.
- **Temporal: use-after-free / double-free / dangling.**
  - Pointer used after `free()`; freeing twice; returning a pointer to a stack local;
    `realloc` returning a new block while the old pointer is still used. Set freed pointers to
    `NULL`; never use a pointer whose owner may have freed it.
- **Uninitialized memory.** Reading a stack/heap variable before assignment (MSan catches it);
  `malloc` (not `calloc`) then reading unset bytes — info-leak or logic bug.
- **NULL deref.** `malloc`/`fopen`/`getenv` return value used without a NULL check → crash/DoS.

## S11 — Format strings

`printf(userStr)`, `fprintf(f, userStr)`, `syslog(pri, userStr)` — user data as the *format*
lets `%n` write memory and `%s`/`%x` read it. The format must always be a string literal;
user data is an argument: `printf("%s", userStr)`.

## S3 / S7 — Command & path (still apply in C)

- `system(cmd)`, `popen(cmd, …)`, `execl/execlp` with a shell — command injection; prefer
  `execve` with a fixed arg vector and no shell.
- Path traversal via `fopen`/`open` on a user-supplied name without canonicalize-and-confine;
  `realpath` + prefix check, or `openat` with `O_NOFOLLOW` under a dir fd.

## Footguns (taint-independent but bug-causing)

- **Integer issues drive memory bugs.** Signed overflow is UB; `int` vs `size_t` mixing;
  implicit narrowing `(int)size_t`; comparing signed/unsigned flips a bounds check. A length
  computed in `int` that goes negative bypasses `if (len < CAP)`.
- **TOCTOU** between `access()`/`stat()` and `open()` on a path an attacker can swap (symlink).
- **`memcpy`/`memmove` overlap** (use `memmove` when ranges overlap); `memcmp` for secret
  comparison is non-constant-time → timing leak (use a constant-time compare).
- **Off-by-one** on `<=` loop bounds and NUL terminator accounting — the classic single-byte
  overflow, still exploitable.
- **Unchecked return values** on `read`/`write`/`recv` (short reads), `malloc` (NULL).

## Sanitizer idioms (what "safe" looks like)

- Every copy is length-bounded against the *destination* size, with NUL accounting.
- Allocation sizes use overflow-checked arithmetic (`__builtin_mul_overflow` / `calloc`).
- Freed pointers nulled; single clear ownership per allocation (document who frees).
- Format strings are literals; secret compares are constant-time.
- The build runs clean under `-Wall -Wextra -Werror` and an ASan+UBSan test pass.

## Notes

- A finding here rarely needs a "tainted source" the way SQLi does — an unchecked length or a
  freed pointer is a bug whether or not the trigger is attacker-controlled — but **reachability
  from input raises severity**: confirm whether the bad length/index/pointer can be driven by
  external data, and say so. Use `references/severity-rubric.md` to land it.
- Prefer pointing at an ASan/UBSan run as the receipt; for a contained PoC the spine's Step 5d
  applies (a minimal harness under isolation), never the project binary itself.
