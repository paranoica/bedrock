#!/usr/bin/env python3
"""
calibration.py — genesis's learning loop. Sparse by nature: the spec-stability signal accrues one
full project at a time (NOT 20–50 votes like design-creator's taste model), so expect it cold for a
long while on a solo project. Kept because it is cheap and DNA-consistent — not because it pays off
soon.

THE BOUNDARY (do not regress — this is the whole point of the file):
a replan FLIP is classified by cause —
  new-decision           a decision that did not exist at the last snapshot (the project grew)   NEUTRAL
  open-question-resolved  a TODO(decision:) that graduated to a settled decision (same slug)      NEUTRAL
  settled-overturned     a previously-settled decision whose content changed / was removed        CANDIDATE
Only `settled-overturned` is even a CANDIDATE interview-quality signal — and it is **NOT charged by
default**, because "the user changed their mind" and "the interview missed it" cannot be separated
mechanically. A flip enters the interview bar ONLY via an explicit human tag `should've-been-caught`.
Default = do NOT charge. Never punish genesis for the user changing their mind.

Commands (--root <dir>, default "."):
  snapshot          store the current anchor state            -> .genesis/spec-snapshot.json
  classify          compare current anchors to the snapshot; append classified flips
                    (settled-overturned recorded charged=false) -> .genesis/calibration.jsonl
  tag <flip_id>     mark a settled-overturned flip should've-been-caught (charged=true)
  report            counts by cause; the interview-bar signal counts CHARGED flips only
"""
import sys, os, json, hashlib, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchors

DOC_FILES = ["decisions.md", "architecture.md", "glossary.md", "open-questions.md"]
NEUTRAL = {"new-decision", "new-spec", "open-question-resolved"}


def kind_of(fname):
    return {"decisions.md": "decisions", "open-questions.md": "open-questions",
            "architecture.md": "architecture", "glossary.md": "glossary"}.get(os.path.basename(fname), "other")


def current_state(root):
    paths = [os.path.join(root, "docs", d) for d in DOC_FILES
             if os.path.exists(os.path.join(root, "docs", d))]
    by_id, _ = anchors.parse_files(paths)
    return {aid: {"kind": kind_of(rec["file"]), "hash": rec["hash"]} for aid, rec in by_id.items()}


def _snap(root): return os.path.join(root, ".genesis", "spec-snapshot.json")
def _log(root):  return os.path.join(root, ".genesis", "calibration.jsonl")
def _counts(flips):
    out = {}
    for f in flips:
        out[f["cause"]] = out.get(f["cause"], 0) + 1
    return out


def classify_flips(prev, cur):
    flips = []
    for aid in sorted(set(prev) | set(cur)):
        p, c = prev.get(aid), cur.get(aid)
        if p and c:
            if p["kind"] == "open-questions" and c["kind"] == "decisions":
                cause = "open-question-resolved"           # graduated — interview did its job
            elif p["kind"] == "decisions" and p["hash"] != c["hash"]:
                cause = "settled-overturned"               # candidate signal
            else:
                continue                                   # unchanged, or non-decision drift — not scored
        elif c and not p:
            cause = "new-decision" if c["kind"] == "decisions" else "new-spec"   # project grew
        else:  # p and not c — removed
            cause = "settled-overturned" if p["kind"] == "decisions" else "open-question-resolved"
        flips.append({"flip_id": hashlib.sha256((aid + cause).encode()).hexdigest()[:8],
                      "anchor": aid, "cause": cause,
                      "candidate": cause == "settled-overturned",  # only this can ever be charged
                      "charged": False})                            # DEFAULT — never auto-charge
    return flips


def cmd_snapshot(root):
    state = current_state(root)
    os.makedirs(os.path.join(root, ".genesis"), exist_ok=True)
    json.dump(state, open(_snap(root), "w"), indent=2, sort_keys=True)
    print(json.dumps({"ok": True, "anchors": len(state)}))


def cmd_classify(root):
    if not os.path.exists(_snap(root)):
        print(json.dumps({"error": "no snapshot; run: calibration.py snapshot first"})); sys.exit(2)
    prev, cur = json.load(open(_snap(root))), current_state(root)
    flips = classify_flips(prev, cur)
    seen = set()
    if os.path.exists(_log(root)):
        for line in open(_log(root)):
            try: seen.add(json.loads(line)["flip_id"])
            except Exception: pass
    new = [f for f in flips if f["flip_id"] not in seen]
    os.makedirs(os.path.join(root, ".genesis"), exist_ok=True)
    with open(_log(root), "a") as fh:
        for f in new:
            fh.write(json.dumps(f) + "\n")
    print(json.dumps({"classified": len(flips), "appended": len(new), "by_cause": _counts(flips),
                      "note": "settled-overturned recorded charged=false by default — NOT in the "
                              "interview bar until a human tags it should've-been-caught"}, indent=2))


def cmd_tag(root, flip_id):
    if not os.path.exists(_log(root)):
        print(json.dumps({"error": "no calibration log"})); sys.exit(2)
    rows = [json.loads(l) for l in open(_log(root)) if l.strip()]
    found = False
    for r in rows:
        if r["flip_id"] == flip_id:
            if r["cause"] != "settled-overturned":
                print(json.dumps({"error": "only settled-overturned flips can be charged",
                                  "cause": r["cause"]})); sys.exit(1)
            r["charged"] = True; found = True
    if not found:
        print(json.dumps({"error": "no such flip_id", "flip_id": flip_id})); sys.exit(2)
    with open(_log(root), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps({"ok": True, "flip_id": flip_id, "charged": True}))


def cmd_report(root):
    rows = [json.loads(l) for l in open(_log(root)) if l.strip()] if os.path.exists(_log(root)) else []
    charged = sum(1 for r in rows if r.get("charged"))
    print(json.dumps({
        "spec_churn_total": len(rows),       # ALL flips — a NEUTRAL signal of spec instability
        "by_cause": _counts(rows),
        "interview_bar_signal": charged,     # ONLY human-tagged should've-been-caught
        "boundary": "new-decision / open-question-resolved are NEUTRAL (never charged). "
                    "settled-overturned is charged ONLY by an explicit human tag. Default = not "
                    "charged — the user changing their mind is not an interview failure.",
        "cold_start": "sparse by design (one project at a time) — do not expect a usable signal soon.",
    }, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["snapshot", "classify", "tag", "report"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    if a.command == "snapshot": cmd_snapshot(a.root)
    elif a.command == "classify": cmd_classify(a.root)
    elif a.command == "tag": cmd_tag(a.root, a.args[0])
    elif a.command == "report": cmd_report(a.root)


if __name__ == "__main__":
    main()
