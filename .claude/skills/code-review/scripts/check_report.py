#!/usr/bin/env python3
"""
check_report.py — turn the "mandatory" report sections from prose imperatives into
a machine-checked contract, so a skipped gate is VISIBLE instead of silently absent.

A skill cannot truly *force* a step from inside a prompt — the model can always cut
it. What we CAN do is make the omission cheap to detect: every required receipt has
a stable anchor, and this linter fails the report if one is missing. Wire it into
the close-out and into evals/run_evals.sh so a report that skipped the grounding gate
(Step 5c) or the coverage block does not pass review unnoticed.

Checks (all deterministic, zero model calls):
  - Scope line                         (was the review actually scoped?)
  - Stack detected line
  - Tools run line                     (degraded-mode honesty)
  - Verification line with a TIER ∈ {A,B,C}
  - Verification line with all four verify_findings counts
      VERIFIED / RELOCATE / CUT / NEEDS_HUMAN   (the grounding gate left a receipt)
  - Verification line carries a hash-bound receipt id (receipt:<12-hex>); with
      --receipt the id, the on-disk file hashes, and the counts are re-checked so a
      hand-typed Verification line cannot pass without verify_findings.py having run
  - Coverage & limits section          (keeps "no findings" honest)
  - No emojis                          (report rule #1)

Usage:
  python3 check_report.py <report.md>                                  # shape only
  python3 check_report.py <report.md> --receipt .review/verify-receipt.json --repo .
  cat report.md | python3 check_report.py -                            # stdin
Exit: 0 = compliant · 1 = missing required receipt(s) · 2 = bad usage
"""
import hashlib
import json
import re
import sys


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_receipt_binding(receipt_path, repo, claimed_id, line_counts):
    """The teeth: prove verify_findings.py actually ran against the real files.

    Returns a list of problems (empty == bound & honest). Checks, in order:
      1. receipt parses and its receipt_id reproduces from its own fields
         (the receipt itself wasn't hand-edited);
      2. the report's `receipt:<id>` equals that id (the report cites THIS run);
      3. every file the receipt claims to have hashed still hashes the same on
         disk (a fabricated receipt can't invent real file hashes);
      4. the four counts on the Verification line equal the receipt summary
         (the numbers weren't typed from memory).
    A hand-written Verification line cannot pass all four without the script
    having produced the artifact against the actual source.
    """
    problems = []
    try:
        receipt = json.loads(open(receipt_path, encoding="utf-8").read())
    except Exception as e:
        return [f"receipt unreadable ({receipt_path}): {e}"]

    core = {
        "findings_sha256": receipt.get("findings_sha256"),
        "files": receipt.get("files", {}),
        "summary": receipt.get("summary", {}),
    }
    recomputed = _sha256_bytes(_canon(core))[:12]
    if recomputed != receipt.get("receipt_id"):
        problems.append("receipt tampered: receipt_id does not match its own fields")

    if claimed_id and claimed_id != receipt.get("receipt_id"):
        problems.append(
            f"report cites receipt:{claimed_id} but the receipt id is {receipt.get('receipt_id')} "
            "— the Verification line is from a different (or invented) run")

    repo = repo or "."
    for rel, want in (receipt.get("files") or {}).items():
        try:
            got = _sha256_bytes(open(f"{repo.rstrip('/')}/{rel}", "rb").read())
        except Exception:
            problems.append(f"receipt file missing on disk: {rel} — receipt is stale or forged")
            continue
        if got != want:
            problems.append(f"receipt file changed since verification: {rel} — receipt is stale or forged")

    # aggregate CUT_* -> CUT for comparison with the report line's single CUT count
    s = receipt.get("summary", {})
    agg = {
        "VERIFIED": s.get("VERIFIED", 0),
        "RELOCATE": s.get("RELOCATE", 0),
        "NEEDS_HUMAN": s.get("NEEDS_HUMAN", 0),
        "CUT": sum(v for k, v in s.items() if str(k).startswith("CUT")),
    }
    for k in ("VERIFIED", "RELOCATE", "CUT", "NEEDS_HUMAN"):
        if k in line_counts and line_counts[k] != agg[k]:
            problems.append(
                f"Verification count {k}={line_counts[k]} contradicts the receipt ({k}={agg[k]}) "
                "— counts were not taken from the verifier run")
    return problems


EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F02F"
    "\U0001F900-\U0001F9FF\U00002190-\U000021FF\U00002B00-\U00002BFF]"
)


def check(text: str, receipt_path=None, repo=None):
    missing = []
    notes = {}

    def has(pat, flags=re.I | re.M):
        return re.search(pat, text, flags) is not None

    if not has(r"^\*\*Scope:\*\*"):
        missing.append("Scope line (**Scope:**)")
    if not has(r"^\*\*Stack detected:\*\*"):
        missing.append("Stack detected line (**Stack detected:**)")
    if not has(r"^\*\*Tools run:\*\*"):
        missing.append("Tools run line (**Tools run:**) — degraded-mode honesty")

    # Verification line: must exist, carry a tier, all four counts, and a receipt id.
    vmatch = re.search(r"^\*\*Verification:\*\*.*$", text, re.I | re.M)
    claimed_id = None
    line_counts = {}
    if not vmatch:
        missing.append("Verification line (**Verification:**) — the grounding-gate receipt")
    else:
        vline = vmatch.group(0)
        tier = re.search(r"\btier\s*([ABC])\b", vline, re.I)
        if not tier:
            missing.append("Verification tier (tier A|B|C) on the Verification line")
        else:
            notes["tier"] = tier.group(1).upper()
        counts = {}
        for key in ("VERIFIED", "RELOCATE", "CUT", "NEEDS_HUMAN"):
            m = re.search(rf"\b{key}\s*=\s*(\d+)\b", vline, re.I)
            if m:
                counts[key] = int(m.group(1))
        line_counts = counts
        if len(counts) < 4:
            absent = [k for k in ("VERIFIED", "RELOCATE", "CUT", "NEEDS_HUMAN") if k not in counts]
            missing.append(
                "verify_findings counts on the Verification line (missing: "
                + ", ".join(absent) + ") — gate left no receipt")
        else:
            notes["counts"] = counts
            if counts["CUT"] > 0:
                notes["cut_warning"] = (
                    f"{counts['CUT']} finding(s) were CUT by the verifier — "
                    "confirm none survived into the report body")
        # the hash-binding token: makes a hand-typed Verification line detectable
        rid = re.search(r"\breceipt:\s*([0-9a-f]{12})\b", vline, re.I)
        if not rid:
            missing.append(
                "receipt hash on the Verification line (receipt:<12-hex>) — the gate receipt "
                "is not hash-bound, so the counts can't be proven to come from a real verifier run")
        else:
            claimed_id = rid.group(1).lower()
            notes["receipt_id"] = claimed_id

    if not has(r"^#+\s*Coverage\s*&\s*limits"):
        missing.append("Coverage & limits section — keeps 'no findings' honest")

    emojis = sorted(set(EMOJI.findall(text)))
    if emojis:
        missing.append("report rule #1: no emojis (found: " + " ".join(emojis) + ")")

    # Cryptographic binding: only runs when the receipt artifact is supplied.
    if receipt_path:
        probs = verify_receipt_binding(receipt_path, repo, claimed_id, line_counts)
        if probs:
            missing.extend("receipt binding: " + p for p in probs)
        else:
            notes["receipt_bound"] = True
    else:
        notes["receipt_bound"] = False

    return missing, notes


def main():
    args = sys.argv[1:]
    receipt_path = None
    repo = None
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--receipt" and i + 1 < len(args):
            receipt_path = args[i + 1]; i += 2; continue
        if args[i] == "--repo" and i + 1 < len(args):
            repo = args[i + 1]; i += 2; continue
        rest.append(args[i]); i += 1
    if not rest:
        print(json.dumps({"error": "usage: check_report.py <report.md|-> [--receipt path] [--repo root]"}))
        sys.exit(2)
    src = rest[0]
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    missing, notes = check(text, receipt_path=receipt_path, repo=repo)
    ok = not missing
    print(json.dumps({"ok": ok, "missing": missing, "notes": notes}, indent=2, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
