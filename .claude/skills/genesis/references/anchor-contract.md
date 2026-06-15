# Anchor contract — the single source of truth for spec anchors

This file defines the anchor grammar, the **one** normalizer + hash, and the reference graph.
It is **authoritative**: the human-facing docs (`interview-taxonomy.md`, the `spec-templates/`)
cite it, and the code (`scripts/anchors.py`, built in increment II) implements **exactly** this —
no second "similar" implementation. `backlog.py` and `analyze_spec.py` both import `anchors.py`.
If the generator and the gate ever disagree on a hash, it is because someone forked this — don't.

## Why anchors exist

Re-derivability rests on each task knowing *which atomic units of the spec it was derived from*
and detecting when those change. Anchors give every atomic spec unit a **stable id** and a
**content hash**, so a change is localized (one unit, not a whole file) and traceable.

## Grammar

An anchor is an HTML comment (invisible in rendered Markdown) placed immediately **before** the
atomic unit it tags:

```
<!-- @anchor <id> [refs:<id>[,<id>]...] -->
```

- `<id>` = `<type>:<slug>` where `slug = [a-z0-9-]+` and `type` is one of, each with its home:
  `decision` (`decisions.md`), `term` (`glossary.md`), `arch` (the Invariants section of
  `architecture.md`), `canon` (a hard rule in `AGENTS.md` a task is bound to — optional; `AGENTS.md`
  is not a must-anchor file). Ids are **stable** — renaming a slug is a structural change.
- `refs:` is **optional**. Zero refs is valid (a decision that depends on nothing parses fine).
- refs are comma-separated; surrounding spaces are tolerated (`refs:term:a, term:b`).
- **refs live in the anchor comment ONLY**, never inferred from the body. The reverse-graph (for
  transitivity) is built from these, not from prose.

Canonical regex (implemented verbatim in `anchors.py`):

```python
ANCHOR_RE = re.compile(
    r"<!--\s*@anchor\s+([a-z]+:[a-z0-9-]+)"      # group 1: id
    r"(?:\s+refs:\s*([a-z0-9:,\s-]*?))?"          # group 2: optional refs blob (may be absent/empty)
    r"\s*-->")
# refs_of(group2): [] if group2 is None/blank else [r.strip() for r in group2.split(",") if r.strip()]
```

## Atomic unit body

The **body** of an anchor is the text from the anchor comment up to (but excluding) the next
anchor comment or end of file, **with the anchor comment line itself removed**. One file holds
many anchored units back-to-back.

## The one normalizer + hash (DO NOT fork)

```python
def normalize(body: str) -> str:
    body = ANCHOR_RE.sub("", body)          # 1. strip any anchor comment lines
    body = re.sub(r"[*_`~#>]", "", body)    # 2. drop Markdown emphasis/heading/quote marks
    body = re.sub(r"\s+", " ", body)        # 3. collapse all whitespace (incl. newlines) to one space
    return body.strip(" .,;:!-")            # 4. trim surrounding whitespace + trailing punctuation

def anchor_hash(body: str) -> str:
    return hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()[:16]
```

Consequences of this exact definition (so both sides agree):
- A **pure formatting/whitespace edit** (bold a word, re-wrap a line, fix indentation) → same hash
  → **no** drift, **no** `needs-review`. This is what stops the mechanism over-firing.
- A **wording change inside the unit** (a real edit to the directive text) → different hash →
  `needs-review` on tasks tracing it. Proportionate: a soft "confirm still valid", not a re-split.
- Trailing-punctuation/typo at the unit edge is absorbed by step 4; a typo *inside the sentence*
  changes a word and therefore the hash — which is the honest behaviour (the text a task implements
  changed), and `needs-review` (not `stale`) keeps the cost low.

## Who computes hashes (critical — the generator never hand-writes them)

genesis (the model) authors prose, anchors, and task **structure**. It **never** writes a hash by
hand. `backlog.py stamp` reads the anchored docs, computes each task's `spec_refs` hashes via
`anchors.anchor_hash`, and fills them in. `analyze_spec.py` recomputes the same way. Because both
call the **same** `anchors.py`, a freshly generated backlog passes `--check` with zero phantom
drift. (In worked examples the hashes show as `h1/h2/h3` precisely because the model does not
compute them — the script does.)

## The reference graph + transitivity

- Forward: an anchor's `refs:` lists the ids it depends on.
- Reverse: `anchors.py` builds id → [ids that ref it]. Cross-cutting types (`term:*`, `arch:*`,
  `canon:*`) are fan-out nodes: when one changes, BFS over the reverse graph marks every anchor
  that references it (transitively) as touched, and tasks tracing those → `needs-review`. This is
  how redefining `term:tutor` reaches tasks with no direct `term:tutor` trace.

## Integrity (enforced by `analyze_spec.py`; never silent-skip)

- **partial annotation** — a must-anchor file (`decisions.md`, `glossary.md`, the Invariants
  section of `architecture.md`) with some units anchored and some not → **CRITICAL**.
- **dangling ref** — a `refs:` id or a task `spec_refs` id with no matching anchor → **CRITICAL**.
- **duplicate id** → **CRITICAL**.

## Evolution — `normalize()` is versioned (changing it is a migration, not a fix)

`anchor_hash` is the critical hinge of the whole system: `backlog.py` and `analyze_spec.py` both
import this one `normalize()`. Therefore **changing `normalize()` re-hashes every anchor in every
seeded project at once** — all existing `spec_refs` mass-desync against the new normalizer.

That is unavoidable and fine, but it means: **changing `normalize()` is a breaking migration, not a
fix.** It must be a deliberate, versioned step (bump a normalizer version, then re-stamp every
backlog), never a silent patch. (Planned: `anchor_hash` records the normalizer version into the
spec-receipt, so a version change is an explicit, visible migration rather than a quiet drift —
the meta-principle "make the violation visible" applied to the template's own self-evolution.)
