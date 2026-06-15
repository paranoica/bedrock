# AI-generated-code ("slop") checklist

Read when the diff looks machine-written: large greenfield chunks, uniform style,
over-commented obvious lines, plausible-but-unverified API usage. LLM-written code
fails in characteristic ways that differ from human bugs. The reviewer is itself an
LLM, so apply extra skepticism here — these are easy to wave through because they
*look* right.

## Hallucinated / wrong API usage
- **Functions, methods, options, or modules that don't exist.** Confident calls to a
  plausible-sounding API the library never shipped, a kwarg that isn't real, an import
  from the wrong module. Verify against the actual installed version, not "this looks
  like how libraries work".
- **Right name, wrong signature/semantics:** correct function, wrong argument order,
  wrong return-value handling, wrong units, ignoring that it returns a Promise/coroutine.
- **Version-mismatched API:** code using an API from a different major version than the
  one in the lockfile (deprecated-and-removed, or not-yet-added).
- **Made-up config keys / env vars** that nothing reads.

## Plausible-but-wrong logic
- **Looks correct, off by a detail:** boundary conditions, inclusive/exclusive ranges,
  timezone/locale assumptions, sign errors, mixed-up variables with similar names.
- **Copy-paste drift:** a block duplicated and adapted, but one variable/field not
  renamed — `userA` logic still referencing `userB`. Very common in generated code.
- **Confident comment contradicting the code.** The comment says what was *intended*;
  the code does something else. Trust neither without checking — verify against behavior.
- **Invented constants / magic numbers** presented as if standard.

## Half-finished work
- **`TODO` / `FIXME` / `pass` / `throw new Error("not implemented")` / `...` left in**
  a path that's wired up as if complete.
- **Stub functions that always return a fixed value** (`return true`, `return []`) but
  are called as real logic.
- **Error handling that's a placeholder:** `except: pass`, `catch (e) {}`, logging the
  error and continuing as if it succeeded.
- **Hardcoded sample/mock data** (example.com, `test@test.com`, `localhost`, dummy keys)
  left on a real path.

## Security theater
- **Validation that looks thorough but is bypassable:** a regex that doesn't anchor,
  an allowlist that's never consulted, a `sanitize()` that returns its input unchanged,
  a check that's computed but whose result is ignored.
- **Defenses that don't compose:** input validated in one handler, the same sink reached
  unvalidated from another.

## Tests that don't test
- **Tests with no meaningful assertions**, tests that assert the mock was called rather
  than that behavior is correct, snapshot tests of nothing, `assert True`.
- **Tests that would pass even if the code were broken** — mock the very thing under test.
- **Diff adds code but no test on a risky path**, or *removes* a test (see migrations-and-compat / the "removed defense" rule).

## Over-engineering / noise
- Needless abstraction layers, config for things that never vary, defensive code for
  impossible states — not a bug, but flag as LOW if it materially hurts readability.

## How to check (don't just eyeball)
- For any non-trivial library call you're not certain about, confirm it exists in the
  pinned version (read the dep, or web-search the API for that version — budget per the
  main workflow).
- Re-read copy-pasted blocks side by side for un-renamed variables.
- For "validation" helpers, read the body (this is the security-general rule too).

## What NOT to flag
- Clean, correct generated code — being AI-written is not itself a defect.
- Verbose-but-correct style, or comments you'd personally trim (that's LOW at most).
- Stubs clearly marked as such and not yet wired into a live path.
