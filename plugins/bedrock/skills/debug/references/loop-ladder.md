# The loop ladder (D048 step 2)

Take the first rung that reproduces the bug:

1. A test at the seam where the bug shows.
2. An HTTP request (curl against the local server) with the exact input.
3. A fixture run diffed against a known-good output.
4. A headless browser script (Playwright) for UI bugs.
5. Replay of a captured trace or a recorded run.
6. A throwaway harness that calls the unit directly.
7. A property or fuzz loop (Hypothesis, fast-check) for "sometimes" bugs.
8. `git bisect run <loop>` when a good version is known.
9. A differential: two versions or two configs on the same input.
10. A human-in-the-loop script, last.

A good loop is fast (seconds), sharp (it asserts the exact symptom, not "something failed")
and deterministic (seeded randomness, fixed time, no network unless the bug is the network).
