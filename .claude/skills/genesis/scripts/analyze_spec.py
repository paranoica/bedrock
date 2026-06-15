#!/usr/bin/env python3
"""
analyze_spec.py — the deterministic half of the spec-analyze gate. Severity-ranked cross-artifact
checks + a hash-bound receipt. The fresh-context spec-verifier subagent is the other half.

Checks (see ../references/anchor-contract.md, invariants.md):
  CRITICAL  partial annotation in a must-anchor file (some units anchored, some not)
  CRITICAL  duplicate anchor id
  CRITICAL  dangling ref (anchor refs / task spec_refs pointing at a non-existent anchor)
  HIGH      a task rests on an OPEN decision (a spec_ref defined in open-questions.md) → not executable
  MEDIUM    a task spec_ref is unstamped (hash null) → run `backlog.py stamp`
  LOW       orphan decision (a decision: anchor in decisions.md no task traces)
  INFO      possible domain noun missing a glossary term (heuristic assist — NOT a hard fail)

Exit non-zero if any CRITICAL (the gate blocks). Writes a hash-bound .genesis/spec-receipt.json.

The receipt is not write-only: `--check` re-hashes docs/ + genesis.tasks.json FROM DISK and compares
to the receipt, so "the gate passed" can't be claimed on a spec that changed afterwards. This is the
gate-freshness stamp (the analogue of the project-map's --check).

Usage:
  analyze_spec.py <root>            run the gate; write the receipt; exit 1 on any CRITICAL
  analyze_spec.py <root> --check    is the receipt fresh vs current docs/tasks? fresh|stale|absent,
                                    exit 0 / 1 / 2 (so a caller/CI can gate)
"""
import sys, os, re, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchors

MUST_ANCHOR = {"decisions.md": "decisions", "glossary.md": "glossary",
               "architecture.md": "architecture"}
ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
_COMMON = {"WHEN", "THEN", "SHALL", "The", "This", "API", "MVP", "OAuth", "ID", "URL", "HTTP"}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def units_with_anchor_state(path, kind):
    """Return atomic units of a must-anchor file and whether each is anchored (the immediately
    preceding non-blank line is an @anchor comment). Used for the partial-annotation check."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    anchor_lines = {text.count("\n", 0, m.start()) for m in anchors.ANCHOR_RE.finditer(text)}
    units, in_inv = [], False
    for i, ln in enumerate(lines):
        is_unit = False
        if kind == "decisions":
            is_unit = bool(re.match(r"^###\s+\S", ln))
        elif kind == "glossary":
            is_unit = bool(re.match(r"^\*\*.+\*\*\s*—", ln))
        elif kind == "architecture":
            if re.match(r"^##\s+Invariants", ln, re.I):
                in_inv = True; continue
            if re.match(r"^##\s+", ln):
                in_inv = False
            is_unit = in_inv and bool(re.match(r"^-\s+\S", ln))
        if is_unit:
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            units.append({"line": i + 1, "anchored": j in anchor_lines, "text": ln.strip()[:70]})
    return units


def analyze(root):
    docs = {d: os.path.join(root, "docs", d) for d in
            ["decisions.md", "architecture.md", "glossary.md", "open-questions.md"]}
    present = {d: p for d, p in docs.items() if os.path.exists(p)}
    by_id, dups = anchors.parse_files(list(present.values()))
    open_ids = set()
    if "open-questions.md" in present:
        open_ids = {a["id"] for a in anchors.parse_text(
            open(present["open-questions.md"], encoding="utf-8", errors="replace").read())}
    findings = []

    def add(sev, code, msg, where=None):
        findings.append({"severity": sev, "code": code, "message": msg, "where": where})

    # CRITICAL — partial annotation
    for fname, kind in MUST_ANCHOR.items():
        if fname not in present:
            continue
        for u in units_with_anchor_state(present[fname], kind):
            if not u["anchored"]:
                add("CRITICAL", "partial-annotation",
                    "unanchored unit in must-anchor file %s: %r" % (fname, u["text"]),
                    "%s:%d" % (fname, u["line"]))
    b = os.path.basename   # spec docs all live in docs/, so the basename is the unambiguous locator
    # CRITICAL — duplicates
    for d in dups:
        add("CRITICAL", "duplicate-anchor", "duplicate anchor id %s" % d["id"],
            "%s (first at %s)" % (b(d["file"]), b(d["first_at"])))
    # CRITICAL — dangling refs (in anchors)
    for aid, rec in by_id.items():
        for r in rec["refs"]:
            if r not in by_id:
                add("CRITICAL", "dangling-ref", "anchor %s refs missing %s" % (aid, r),
                    "%s:%d" % (b(rec["file"]), rec["line"]))

    # task-level checks
    tasks_path = os.path.join(root, "genesis.tasks.json")
    traced = set()
    if os.path.exists(tasks_path):
        tobj = json.load(open(tasks_path))
        for t in tobj.get("tasks", []):
            sr = t.get("spec_refs") or {}
            for aid, h in sr.items():
                traced.add(aid)
                if aid not in by_id:
                    add("CRITICAL", "dangling-ref",
                        "task %s spec_ref %s has no anchor" % (t["id"], aid), t["id"])
                elif h is None:
                    add("MEDIUM", "unstamped", "task %s spec_ref %s unstamped — run backlog.py stamp"
                        % (t["id"], aid), t["id"])
                if aid in open_ids:
                    add("HIGH", "rests-on-open-decision",
                        "task %s depends on OPEN decision %s — not execution-ready until resolved"
                        % (t["id"], aid), t["id"])
            # INFO — domain-noun heuristic on acceptance
            gloss_words = set()
            for i in by_id:
                if i.startswith("term:"):
                    gloss_words.add(i.split(":", 1)[1].replace("-", "").lower())
            for ac in t.get("acceptance", []):
                for w in re.findall(r"\b[A-Z][a-z]{3,}\b", ac):
                    if w not in _COMMON and w.lower() not in gloss_words:
                        add("INFO", "maybe-missing-term",
                            "task %s acceptance uses %r — domain term without a glossary anchor? "
                            "(heuristic; anchor it or confirm it's not a domain term)" % (t["id"], w), t["id"])
    # LOW — orphan decisions
    for aid, rec in by_id.items():
        if aid.startswith("decision:") and rec["file"].endswith("decisions.md") and aid not in traced:
            add("LOW", "orphan-decision", "decision %s has no task tracing it" % aid,
                "%s:%d" % (b(rec["file"]), rec["line"]))

    # de-dup INFO noise (same word reported once per task is fine; collapse identical)
    seen = set(); uniq = []
    for f in findings:
        k = (f["severity"], f["code"], f["message"])
        if k not in seen:
            seen.add(k); uniq.append(f)
    uniq.sort(key=lambda f: ORDER.index(f["severity"]))
    summary = {s: sum(1 for f in uniq if f["severity"] == s) for s in ORDER}

    # receipt (hash-bound: docs + tasks content + summary)
    files = {}
    for p in list(present.values()) + ([tasks_path] if os.path.exists(tasks_path) else []):
        files[os.path.relpath(p, root)] = _sha(open(p, "rb").read())[:16]
    core = {"files": files, "summary": summary}
    rid = _sha(json.dumps(core, sort_keys=True).encode())[:12]
    receipt = {"receipt_version": 1, "receipt_id": rid, **core}
    out_dir = os.path.join(root, ".genesis")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "spec-receipt.json"), "w") as f:
        json.dump(receipt, f, indent=2)

    return uniq, summary, rid


def _present_files(root):
    out = {}
    for d in ["decisions.md", "architecture.md", "glossary.md", "open-questions.md"]:
        p = os.path.join(root, "docs", d)
        if os.path.exists(p):
            out[os.path.relpath(p, root)] = p
    tp = os.path.join(root, "genesis.tasks.json")
    if os.path.exists(tp):
        out[os.path.relpath(tp, root)] = tp
    return out


def check(root):
    """Freshness of the gate receipt vs current docs/tasks — gives the receipt a consumer + teeth."""
    rp = os.path.join(root, ".genesis", "spec-receipt.json")
    if not os.path.exists(rp):
        return {"state": "absent", "reason": "no .genesis/spec-receipt.json — run the gate first"}
    try:
        receipt = json.load(open(rp))
    except Exception as e:
        return {"state": "absent", "reason": "receipt unreadable (%s); re-run the gate" % e}
    cur = {rel: _sha(open(p, "rb").read())[:16] for rel, p in _present_files(root).items()}
    old = receipt.get("files", {})
    changed = sorted((set(cur) | set(old)) - {k for k in cur if cur.get(k) == old.get(k)})
    if not changed:
        return {"state": "fresh", "receipt_id": receipt.get("receipt_id")}
    return {"state": "stale", "reason": "spec/tasks changed since the gate ran — its result is no "
            "longer valid", "changed": changed, "hint": "re-run: analyze_spec.py <root>"}


def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "usage: analyze_spec.py <root> [--check]"})); sys.exit(2)
    root = next((a for a in args if not a.startswith("-")), ".")
    if "--check" in args:
        res = check(root)
        print(json.dumps(res, indent=2))
        sys.exit({"fresh": 0, "stale": 1, "absent": 2}.get(res["state"], 2))
    findings, summary, rid = analyze(root)
    print(json.dumps({"summary": summary, "receipt_id": rid, "findings": findings}, indent=2))
    sys.exit(1 if summary["CRITICAL"] else 0)


if __name__ == "__main__":
    main()
