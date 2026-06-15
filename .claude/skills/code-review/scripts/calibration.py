#!/usr/bin/env python3
"""
Track how well-calibrated the reviewer's confidence is over time.

Each finding ships with a predicted probability that it's a true positive
(derived from its confidence label). When a finding is later resolved
(confirmed real or dismissed as FP), record the outcome here. Over many
reviews this yields a Brier score and a calibration table, so "CRITICAL,
high confidence" becomes a *measured* claim instead of a vibe.

Brier score = mean((p - outcome)^2), lower is better (0 = perfect).

Usage:
  # map a confidence label to a probability (for the report):
  python3 calibration.py p high            -> 0.9

  # record a resolved finding:
  python3 calibration.py record <p> <outcome>   # outcome: 1=true positive, 0=false positive
  python3 calibration.py record 0.9 1

  # show the running scorecard:
  python3 calibration.py report

Log lives at $CLAUDE_CACHE_DIR/calibration.jsonl (default .claude/cache/).
stdlib only.
"""
import json
import os
import sys
import time
from pathlib import Path

CACHE_DIR = Path(os.environ.get("CLAUDE_CACHE_DIR", ".claude/cache"))
LOG = CACHE_DIR / "calibration.jsonl"

# confidence label -> predicted p(true positive). Tune from your own report data.
LABEL_P = {
    "high": 0.9,
    "medium": 0.65,
    "needs verification": 0.35,
    "low": 0.35,
}


def label_to_p(label: str):
    return LABEL_P.get((label or "").strip().lower(), 0.5)


def record(p: float, outcome: int):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"p": p, "outcome": int(outcome), "ts": time.time()}) + "\n")


def report():
    if not LOG.exists():
        return {"n": 0, "note": "no resolved findings logged yet"}
    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    n = len(rows)
    if n == 0:
        return {"n": 0}
    brier = sum((r["p"] - r["outcome"]) ** 2 for r in rows) / n
    # calibration table: predicted bucket vs observed TP rate
    buckets = {}
    for r in rows:
        b = f"{int(r['p'] * 10) * 10}-{int(r['p'] * 10) * 10 + 10}%"
        buckets.setdefault(b, []).append(r["outcome"])
    table = {
        b: {"count": len(v), "observed_tp_rate": round(sum(v) / len(v), 3)}
        for b, v in sorted(buckets.items())
    }
    observed = sum(r["outcome"] for r in rows) / n
    return {
        "n": n,
        "brier_score": round(brier, 4),
        "overall_observed_tp_rate": round(observed, 3),
        "calibration_table": table,
        "interpretation": "lower brier = better; observed rate should track the bucket",
    }


def main():
    a = sys.argv[1:]
    if not a:
        print(json.dumps({"error": "see --help / docstring"}))
        sys.exit(2)
    cmd = a[0]
    if cmd == "p":
        print(label_to_p(" ".join(a[1:])))
    elif cmd == "record" and len(a) >= 3:
        record(float(a[1]), int(a[2]))
        print(json.dumps({"recorded": {"p": float(a[1]), "outcome": int(a[2])}}))
    elif cmd == "report":
        print(json.dumps(report(), indent=2))
    else:
        print(json.dumps({"error": f"bad args: {a}"}))
        sys.exit(2)


if __name__ == "__main__":
    main()
