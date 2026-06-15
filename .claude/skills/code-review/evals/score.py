#!/usr/bin/env python3
"""
Score a candidate review against expected labels.

Usage: python3 score.py <candidate_findings.json> <expected.json> [repo_root]

Metrics:
  recall            fraction of must_catch issues the review found
  false_positives   count of findings on must_not_flag files
  hallucinations    findings whose quote/file fail verify_findings (ungrounded)
A passing review: recall == 1.0, false_positives == 0, hallucinations == 0.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    cand = json.loads(Path(sys.argv[1]).read_text()).get("findings", [])
    exp = json.loads(Path(sys.argv[2]).read_text())
    repo = sys.argv[3] if len(sys.argv) > 3 else str(HERE)

    # recall over must_catch — a hit needs BOTH the right category AND a line
    # near the expected one. The old `category OR line` let a wrong-category
    # finding that merely landed near the right line count as caught, inflating
    # recall (and therefore F1, which the tournament regression-guard trusts).
    caught = []
    for need in exp.get("must_catch", []):
        want_cat = need.get("category", "").lower()
        near = need.get("near_line")
        hit = any(
            f.get("file", "").endswith(Path(need["file"]).name)
            and want_cat
            and want_cat in (f.get("category", "").lower() or f.get("id", "").lower() or "")
            and (near is None
                 or abs((f.get("lines") or [0])[0] - near) <= 3)
            for f in cand)
        caught.append((need.get("tag", need["file"]), hit))
    recall = sum(1 for _, h in caught if h) / max(1, len(caught))

    # false positives on must_not_flag files
    nf = {Path(x["file"]).name for x in exp.get("must_not_flag", [])}
    fps = [f for f in cand if Path(f.get("file","")).name in nf]

    # precision / F1 — F1 is the metric that punishes BOTH failure modes
    # (missing real bugs AND crying wolf), which is what review credibility hinges on.
    tp = sum(1 for _, h in caught if h)
    fp = len(fps)
    precision = tp / max(1, tp + fp)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # hallucinations via the deterministic verifier
    vf = subprocess.run(
        [sys.executable, str(HERE.parent / "scripts" / "verify_findings.py"),
         sys.argv[1], repo],
        capture_output=True, text=True)
    vout = json.loads(vf.stdout or "{}")
    halluc = [r for r in vout.get("results", []) if r["verdict"].startswith("CUT")]

    report = {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "f1": round(f1, 3),
        "caught": caught,
        "false_positives": len(fps),
        "false_positive_ids": [f.get("id") for f in fps],
        "hallucinations": len(halluc),
        "hallucination_ids": [r["id"] for r in halluc],
        "pass": recall == 1.0 and not fps and not halluc,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["pass"] else 1)

if __name__ == "__main__":
    main()
