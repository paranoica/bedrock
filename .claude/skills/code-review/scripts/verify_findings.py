#!/usr/bin/env python3
"""
Ground every finding against the actual source — "tool receipts, not vibes".

The reviewer is required to emit findings as JSON before writing the report.
This script checks each finding's *receipt* deterministically and returns a
verdict the reviewer MUST honor:

  VERIFIED        quote found at the claimed line range -> keep as-is
  RELOCATE        quote found, but at different lines  -> keep, fix line numbers
  CUT_NO_FILE     file does not exist                  -> drop (fabricated path)
  CUT_NO_QUOTE    quote not found anywhere in the file -> drop (hallucinated code)
  CUT_BAD_CVE     cve id absent from OSV output        -> drop (fabricated CVE)
  NEEDS_HUMAN     no quote/lines provided to check     -> keep but mark unverified

This catches the top LLM-review failure modes (invented line numbers, paraphrased
"quotes", made-up CVE IDs) with zero model calls.

Usage:
  python3 verify_findings.py <findings.json> [repo_root] [osv_output.json]

findings.json schema:
  {"findings": [
     {"id":"F1","severity":"CRITICAL","file":"app/x.py","lines":[42,45],
      "quote":"cursor.execute(f\"... {uid}\")","cve":null}, ...]}
"""
import hashlib
import json
import re
import sys
from pathlib import Path

RECEIPT_VERSION = 1


def _canon(obj) -> bytes:
    """Stable serialization so the receipt id is reproducible in any context."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def emit_receipt(findings_src: Path, repo: Path, results: list, summary: dict) -> dict:
    """Write a hash-bound receipt so check_report.py can prove this script
    actually ran against the real files — a hand-typed Verification line cannot
    forge it without reproducing the on-disk file hashes.

    receipt_id binds: the findings.json content + the sha256 of every source
    file the verification read + the verdict summary. check_report --receipt
    re-hashes those files FROM DISK; a fabricated or stale receipt won't match.
    """
    findings_sha = _sha256_bytes(findings_src.read_bytes())
    files = {}
    for r in results:
        fp = r.get("file")
        # only files we actually opened and located code in (real source we depended on)
        if fp and r.get("verdict") in ("VERIFIED", "RELOCATE"):
            p = repo / fp
            if p.exists() and p.is_file():
                files[fp] = _sha256_bytes(p.read_bytes())
    core = {"findings_sha256": findings_sha, "files": files, "summary": summary}
    receipt_id = _sha256_bytes(_canon(core))[:12]
    receipt = {"receipt_version": RECEIPT_VERSION, "receipt_id": receipt_id, **core}
    out_dir = repo / ".review"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "verify-receipt.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {"path": str(out_path), "receipt_id": receipt_id}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def collect_cve_ids(osv: dict):
    ids = set()
    for v in osv.get("vulnerable", []) or []:
        for a in v.get("advisories", []) or []:
            if a.get("id"):
                ids.add(a["id"].upper())
            for al in a.get("aliases", []) or []:
                ids.add(al.upper())
    return ids


def locate(quote_n: str, lines: list, prefer_line=None):
    """Return 1-based (start,end) of the line window whose normalized text
    contains the normalized quote, or None.

    When `prefer_line` is given (the finding's claimed start line), choose the
    occurrence nearest to it rather than the first one in the file. This stops a
    short verbatim quote (e.g. a bare sink token that also appears in benign code
    earlier) from being "relocated" off a correct finding onto an unrelated line.
    With no claim, behavior is unchanged: smallest window, first position.
    """
    if not quote_n:
        return None
    norm_lines = [norm(l) for l in lines]
    n = len(lines)
    # single-line matches first (tightest); fall back to multi-line windows.
    singles = [(i + 1, i + 1) for i, nl in enumerate(norm_lines) if quote_n in nl]
    if singles:
        windows = singles
    else:
        windows = []
        for w in range(2, min(n, 12) + 1):
            for i in range(0, n - w + 1):
                joined = norm(" ".join(norm_lines[i:i + w]))
                if quote_n in joined:
                    windows.append((i + 1, i + w))
        if not windows:
            return None
    if prefer_line is not None:
        # nearest start to the claim; ties keep the earlier/smaller window.
        return min(windows, key=lambda se: (abs(se[0] - prefer_line), se[0], se[1] - se[0]))
    return windows[0]


def verify_one(f: dict, repo: Path, cve_ids: set, osv_provided: bool):
    out = {"id": f.get("id"), "severity": f.get("severity"), "file": f.get("file")}
    # CVE findings
    cve = (f.get("cve") or "").upper()
    if cve:
        if not osv_provided:
            out.update(verdict="NEEDS_HUMAN",
                       reason=f"no OSV output supplied; cannot confirm {cve} — re-run check_cves and pass it")
            return out
        if cve not in cve_ids:
            out.update(verdict="CUT_BAD_CVE",
                       reason=f"{cve} not present in OSV output for this project")
            return out
        out.update(verdict="VERIFIED", reason="cve id present in OSV output")
        return out

    fp = f.get("file")
    if not fp:
        out.update(verdict="NEEDS_HUMAN", reason="no file path on finding")
        return out
    path = repo / fp
    if not path.exists():
        out.update(verdict="CUT_NO_FILE", reason=f"{fp} does not exist")
        return out

    quote_n = norm(f.get("quote", ""))
    claimed = f.get("lines") or []
    if not quote_n:
        out.update(verdict="NEEDS_HUMAN", reason="no quote to verify against source")
        return out

    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception as e:
        out.update(verdict="NEEDS_HUMAN", reason=f"cannot read file: {e}")
        return out

    found = locate(quote_n, lines, prefer_line=(claimed[0] if claimed else None))
    if not found:
        out.update(verdict="CUT_NO_QUOTE",
                   reason="quoted code not found in file (paraphrase or hallucination)")
        return out

    out["actual_lines"] = list(found)
    if claimed and len(claimed) >= 1:
        cs = claimed[0]
        ce = claimed[1] if len(claimed) > 1 else claimed[0]
        # tolerate a small off-by-a-few drift as VERIFIED
        if abs(cs - found[0]) <= 2:
            out.update(verdict="VERIFIED", reason="quote matches claimed lines")
        else:
            out.update(verdict="RELOCATE",
                       reason=f"quote is really at {found[0]}-{found[1]}, "
                              f"not {cs}-{ce}; fix the line numbers")
    else:
        out.update(verdict="RELOCATE", reason=f"no lines claimed; quote at {found[0]}-{found[1]}")
    return out


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: verify_findings.py <findings.json> [repo] [osv.json]"}))
        sys.exit(2)
    findings = json.loads(Path(sys.argv[1]).read_text()).get("findings", [])
    repo = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    cve_ids = set()
    osv_provided = False
    if len(sys.argv) > 3 and Path(sys.argv[3]).exists():
        osv_provided = True
        try:
            cve_ids = collect_cve_ids(json.loads(Path(sys.argv[3]).read_text()))
        except Exception:
            pass

    results = [verify_one(f, repo, cve_ids, osv_provided) for f in findings]
    summary = {}
    for r in results:
        summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1
    cut = [r for r in results if r["verdict"].startswith("CUT")]
    receipt = emit_receipt(Path(sys.argv[1]), repo, results, summary)
    print(json.dumps({
        "summary": summary,
        "receipt": receipt,
        "must_cut": cut,
        "must_relocate": [r for r in results if r["verdict"] == "RELOCATE"],
        "results": results,
    }, indent=2))
    # non-zero exit if anything must be cut, so callers/CI can gate
    sys.exit(1 if cut else 0)


if __name__ == "__main__":
    main()
