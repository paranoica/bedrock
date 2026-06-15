#!/usr/bin/env python3
"""
record_outcome.py — close the loop. When a finding is resolved (you accepted it,
or dismissed it as a false positive), record it so the *next* review is smarter:

  - .review/outcomes.jsonl   append-only audit of every resolution
  - .review/suppressions.json  FP signatures NOT to re-flag (category + path glob
                               + a quote fingerprint), so the same wrong call
                               doesn't get made twice
  - .review/standards.md     human-readable accepted conventions, appended
  - forwards to scripts/calibration.py so the Brier scorecard stays fed

This is the cheap version of what graph reviewers do over weeks: learn the team's
conventions and stop crying wolf on the same pattern. It is advisory — Step 0b
LOADS suppressions and treats a match as "default-suppress, re-flag only with new
evidence", never as a hard mute on a genuinely different bug.

Usage:
  # a finding was a false positive -> suppress its pattern
  record_outcome.py fp  --category Injection --file app/api.py \
      --quote 'db.$queryRaw`...`' --reason "Prisma tagged template, parameterized"

  # a finding was real and accepted -> log + (optional) note a standard
  record_outcome.py tp  --category Auth --file app/auth.py \
      --quote 'verify(token)' --p 0.9

  # record an accepted convention as a standard
  record_outcome.py standard --text "All money math uses Decimal, never float"

  # list current suppressions (Step 0b reads this)
  record_outcome.py list

  --root <repo> (default .)   ; stdlib only.
"""
import sys, os, json, time, hashlib, argparse, subprocess, fnmatch
from pathlib import Path

HERE = Path(__file__).resolve().parent

def review_dir(root): 
    d = Path(root) / ".review"; d.mkdir(parents=True, exist_ok=True); return d

def fingerprint(category, quote):
    return hashlib.sha256(f"{category}\n{(quote or '').strip()}".encode()).hexdigest()[:12]

def load_suppressions(root):
    f = review_dir(root) / "suppressions.json"
    if f.exists():
        try: return json.loads(f.read_text())
        except Exception: return {"suppressions": []}
    return {"suppressions": []}

def save_suppressions(root, data):
    (review_dir(root) / "suppressions.json").write_text(json.dumps(data, indent=2))

def append_outcome(root, rec):
    with (review_dir(root) / "outcomes.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")

def append_standard(root, text):
    p = review_dir(root) / "standards.md"
    if not p.exists():
        p.write_text("# Learned conventions (this repo)\n\n"
                     "Accepted standards observed across reviews. Honor these; a change\n"
                     "that violates one is a finding.\n\n")
    with p.open("a") as f:
        f.write(f"- {text.strip()}  _(recorded {time.strftime('%Y-%m-%d')})_\n")

def calibrate(p, outcome):
    cal = HERE / "calibration.py"
    if cal.exists() and p is not None:
        subprocess.run([sys.executable, str(cal), "record", str(p), str(outcome)],
                       capture_output=True)

def matches_suppression(root, category, file, quote):
    """Step 0b helper: does this candidate finding match a known FP signature?"""
    data = load_suppressions(root)
    fp = fingerprint(category, quote)
    for s in data["suppressions"]:
        if s.get("fingerprint") == fp:
            return s
        if (s.get("category","").lower() == (category or "").lower()
                and fnmatch.fnmatch(file or "", s.get("file_glob","*"))
                and s.get("quote_substr") and quote and s["quote_substr"] in quote):
            return s
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["fp", "tp", "standard", "list", "match"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--category", default="")
    ap.add_argument("--file", default="")
    ap.add_argument("--quote", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--p", type=float, default=None)
    a = ap.parse_args()

    if a.action == "list":
        print(json.dumps(load_suppressions(a.root), indent=2)); return

    if a.action == "match":
        m = matches_suppression(a.root, a.category, a.file, a.quote)
        print(json.dumps({"suppressed": bool(m), "rule": m})); return

    if a.action == "standard":
        if not a.text: print(json.dumps({"error":"--text required"})); sys.exit(2)
        append_standard(a.root, a.text)
        print(json.dumps({"ok": True, "standard_added": a.text})); return

    rec = {"action": a.action, "category": a.category, "file": a.file,
           "fingerprint": fingerprint(a.category, a.quote),
           "ts": time.time()}

    if a.action == "fp":
        data = load_suppressions(a.root)
        if not any(s.get("fingerprint") == rec["fingerprint"] for s in data["suppressions"]):
            data["suppressions"].append({
                "fingerprint": rec["fingerprint"],
                "category": a.category,
                "file_glob": (os.path.dirname(a.file) + "/*") if a.file else "*",
                "quote_substr": (a.quote or "")[:80],
                "reason": a.reason, "ts": rec["ts"]})
            save_suppressions(a.root, data)
        append_outcome(a.root, {**rec, "outcome": 0, "reason": a.reason})
        calibrate(a.p, 0)
        print(json.dumps({"ok": True, "suppressed": rec["fingerprint"], "reason": a.reason}))
    else:  # tp
        append_outcome(a.root, {**rec, "outcome": 1, "p": a.p})
        calibrate(a.p, 1)
        print(json.dumps({"ok": True, "logged_true_positive": rec["fingerprint"]}))

if __name__ == "__main__":
    main()
