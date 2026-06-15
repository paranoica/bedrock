#!/usr/bin/env python3
"""
anchors.py — THE single implementation of the spec-anchor contract.

Authoritative spec: ../references/anchor-contract.md. `backlog.py` and `analyze_spec.py` BOTH
import this module; nothing re-implements normalize()/anchor_hash(). genesis (the model) never
writes a hash by hand — `backlog.py stamp` computes them here. One implementation ⇒ a freshly
generated backlog has zero phantom drift, by construction.

CLI:
  anchors.py <file...> [--graph]     # dump id -> {hash, refs, file, line}; --graph adds reverse edges
"""
import re, hashlib, json, os

# Grammar (verbatim from anchor-contract.md). refs are OPTIONAL; zero refs is valid.
ANCHOR_RE = re.compile(
    r"<!--\s*@anchor\s+([a-z]+:[a-z0-9-]+)"      # group 1: id  (type:slug)
    r"(?:\s+refs:\s*([a-z0-9:,\s-]*?))?"          # group 2: optional refs blob (may be absent/empty)
    r"\s*-->")

CROSS_CUTTING = ("term:", "arch:", "canon:")


def refs_of(blob):
    """refs are read from the anchor comment ONLY, never inferred from the body."""
    if not blob:
        return []
    return [r.strip() for r in blob.split(",") if r.strip()]


def normalize(body):
    """The one normalizer. Pure-formatting/whitespace edits → identical output (no drift);
    a wording change → different output (drift). See anchor-contract.md for the consequences."""
    body = ANCHOR_RE.sub("", body)            # 1. strip any anchor comment lines
    body = re.sub(r"[*_`~#>]", "", body)      # 2. drop Markdown emphasis/heading/quote marks
    body = re.sub(r"\s+", " ", body)          # 3. collapse all whitespace to one space
    return body.strip(" .,;:!-")              # 4. trim surrounding whitespace + trailing punctuation


def anchor_hash(body):
    return hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()[:16]


def parse_text(text, path=None):
    """Ordered list of {id, refs, body, hash, line, file}. A unit's body runs from its anchor
    to the next anchor (or EOF), with the anchor comment line itself removed by normalize()."""
    matches = list(ANCHOR_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        body = text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        out.append({"id": m.group(1), "refs": refs_of(m.group(2)),
                    "body": body, "hash": anchor_hash(body),
                    "line": text.count("\n", 0, m.start()) + 1, "file": path})
    return out


def parse_files(paths):
    """Return (by_id, duplicates). First occurrence of an id wins; later ones are duplicates."""
    by_id, dups = {}, []
    for p in paths:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for a in parse_text(text, os.path.relpath(p)):
            if a["id"] in by_id:
                dups.append({"id": a["id"], "file": a["file"], "line": a["line"],
                             "first_at": by_id[a["id"]]["file"]})
            else:
                by_id[a["id"]] = a
    return by_id, dups


def forward_closure(roots, by_id):
    """Ids reachable by following refs forward from `roots` (the roots themselves included).
    Missing ids (refs to a non-existent anchor) are returned too, so callers can flag dangling."""
    seen, stack = set(), list(roots)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        rec = by_id.get(cur)
        if rec:
            stack.extend(r for r in rec["refs"] if r not in seen)
    return seen


def reverse_graph(by_id):
    rev = {}
    for aid, rec in by_id.items():
        for r in rec["refs"]:
            rev.setdefault(r, set()).add(aid)
    return rev


def transitive_referrers(changed_ids, by_id):
    """All ids that (transitively) reference any changed id — reverse BFS. The cross-cutting
    safety net + reporting aid. (Day-to-day transitivity is realized at stamp time, which bakes
    each task's full forward closure into its spec_refs, so re-derive stays a simple per-id diff.)"""
    rev = reverse_graph(by_id)
    seen, stack = set(), list(changed_ids)
    while stack:
        for ref in rev.get(stack.pop(), ()):
            if ref not in seen:
                seen.add(ref)
                stack.append(ref)
    return seen


def is_cross_cutting(aid):
    return aid.startswith(CROSS_CUTTING)


def _cli():
    import argparse, sys
    ap = argparse.ArgumentParser(description="dump spec anchors + hashes (the one contract impl)")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--graph", action="store_true", help="also print the reverse refs graph")
    a = ap.parse_args()
    by_id, dups = parse_files(a.files)
    out = {"count": len(by_id), "duplicates": dups,
           "anchors": {aid: {"hash": r["hash"], "refs": r["refs"], "file": r["file"], "line": r["line"]}
                       for aid, r in sorted(by_id.items())}}
    if a.graph:
        out["reverse_graph"] = {k: sorted(v) for k, v in sorted(reverse_graph(by_id).items())}
    print(json.dumps(out, indent=2))
    sys.exit(1 if dups else 0)


if __name__ == "__main__":
    _cli()
