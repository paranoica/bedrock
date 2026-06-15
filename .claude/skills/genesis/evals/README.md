# genesis evals

Lightweight regression for the load-bearing mechanisms. Run before shipping any change to
`scripts/anchors.py`, `backlog.py`, or `analyze_spec.py`.

## `seam_test.py` — the anchor/normalizer seam + gate teeth

```
python3 .claude/skills/genesis/evals/seam_test.py
```

Self-contained (copies `fixtures/storage-marketplace/` to a temp dir, asserts, cleans up). It locks
in the behaviour proven during the build:

- anchors are **deterministic** across runs;
- `stamp` expands each task's `spec_refs` to the **forward closure** (T010 picks up `term:escrow` and
  the OPEN `decision:payment-provider`);
- a freshly stamped spec has **zero drift** on `re-derive` (generator and gate share one `anchor_hash`);
- **CONTENT** edit → `needs-review` (soft); **FORMATTING-only** edit → **no drift** (the normalizer
  earns its keep); **STRUCTURAL** rename → `stale`, and a `done` task → `needs-review` (never silently
  un-done); **TRANSITIVE** term edit → `needs-review` via the stamped closure;
- `analyze_spec` returns **0 CRITICAL** on the clean spec, flags T010 **HIGH** (rests on an open
  decision), and returns **CRITICAL + exit 1** on a partial-annotation;
- `backlog.py validate` exits **1** when `PLAN.md` is hand-edited (the status-seam teeth).

## `fixtures/storage-marketplace/`

A deliberately non-trivial spec (data-model + auth + money + an open decision) used by `seam_test.py`.
Kept pristine and **unstamped** so the test's `stamp` step is meaningful.
