#!/usr/bin/env python3
"""
Change-risk score for a diff / PR. Routes reviewer attention and flags PRs that
are too big or mix unrelated concerns (which make human review unreliable).

Deterministic, stdlib only. Two ways to feed it the diff:

  # A) let it read git (run inside the repo):
  python3 change_risk.py --git <base_ref> [repo_root]

  # B) hand it a numstat-style JSON (testable / CI):
  python3 change_risk.py --files changes.json [repo_root]
      changes.json: {"files":[{"path":"app/auth.py","added":40,"removed":5}, ...]}

Output JSON:
  per-file risk, an overall 0-100 score, and flags:
    too_big            churn or file count past review-reliability thresholds
    mixed_concerns     diff spans many unrelated areas (refactor+feature+fix+migration)
    risky_no_tests     source churn in sensitive files with no matching test churn
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# path -> criticality weight (blast radius if it breaks)
CRIT = [
    (re.compile(r"(auth|login|session|token|password|oauth|saml|jwt)", re.I), 5),
    (re.compile(r"(pay|billing|charge|invoice|wallet|ledger|money|price)", re.I), 5),
    (re.compile(r"(crypto|secret|key|cipher|sign|hash|kms|vault)", re.I), 5),
    (re.compile(r"(migrat|schema|/sql/|\.sql$|alembic|prisma)", re.I), 4),
    (re.compile(r"(security|permission|access|acl|role|guard|middleware)", re.I), 4),
    (re.compile(r"(api/|routes?/|handler|controller|endpoint|view)", re.I), 3),
    (re.compile(r"(config|settings|env|infra|deploy|dockerfile|\.ya?ml$)", re.I), 3),
    (re.compile(r"(test|spec|__tests__|\.test\.|\.spec\.)", re.I), 1),
    (re.compile(r"(readme|docs?/|\.md$|changelog|license)", re.I), 1),
]
DEFAULT_CRIT = 2

TOO_BIG_CHURN = 800     # lines added+removed past which review reliability drops
TOO_BIG_FILES = 40

# rough "concern" buckets to detect a PR doing too many things at once
CONCERN = [
    ("migration", re.compile(r"(migrat|alembic|\.sql$|schema)", re.I)),
    ("config",    re.compile(r"(config|settings|\.env|\.ya?ml$|dockerfile|ci|workflow)", re.I)),
    ("deps",      re.compile(r"(package\.json|lock|requirements|pyproject|go\.mod|Cargo)", re.I)),
    ("tests",     re.compile(r"(test|spec|__tests__)", re.I)),
    ("docs",      re.compile(r"(\.md$|docs?/|readme)", re.I)),
    ("frontend",  re.compile(r"\.(tsx?|jsx?|css|scss|vue|svelte)$", re.I)),
    ("backend",   re.compile(r"\.(py|go|rb|java|rs|php)$", re.I)),
]


def criticality(path: str) -> int:
    for rx, w in CRIT:
        if rx.search(path):
            return w
    return DEFAULT_CRIT


def is_test(path: str) -> bool:
    return bool(re.search(r"(test|spec|__tests__|\.test\.|\.spec\.)", path, re.I))


def is_sensitive(path: str) -> bool:
    return criticality(path) >= 4 and not is_test(path)


def callers_estimate(path: str, repo: Path) -> int:
    """Best-effort blast radius: how many files import/reference this module."""
    stem = Path(path).stem
    if not stem or stem in ("index", "__init__", "main"):
        return 0
    n = 0
    try:
        for f in repo.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (
                    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rb"):
                continue
            if str(f).endswith(path):
                continue
            try:
                if re.search(rf"\b{re.escape(stem)}\b", f.read_text(errors="ignore")):
                    n += 1
            except Exception:
                continue
            if n > 200:
                break
    except Exception:
        pass
    return n


def from_git(base: str, repo: Path):
    out = subprocess.run(["git", "-C", str(repo), "diff", "--numstat", base],
                         capture_output=True, text=True)
    files = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added = 0 if parts[0] == "-" else int(parts[0])
            removed = 0 if parts[1] == "-" else int(parts[1])
            files.append({"path": parts[2], "added": added, "removed": removed})
    return files


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(json.dumps({"error": "usage: change_risk.py (--git <base> | --files <json>) [repo]"}))
        sys.exit(2)
    mode, src = args[0], args[1]
    repo = Path(args[2]) if len(args) > 2 else Path(".")

    if mode == "--git":
        files = from_git(src, repo)
    elif mode == "--files":
        files = json.loads(Path(src).read_text()).get("files", [])
    else:
        print(json.dumps({"error": f"unknown mode {mode}"}))
        sys.exit(2)

    if not files:
        print(json.dumps({"error": "no changed files", "score": 0}))
        return

    per_file, total_churn, weighted = [], 0, 0.0
    concerns = set()
    sensitive_churn, test_churn = 0, 0
    for f in files:
        path = f["path"]
        churn = int(f.get("added", 0)) + int(f.get("removed", 0))
        total_churn += churn
        crit = criticality(path)
        callers = callers_estimate(path, repo)
        risk = churn * crit * (1 + min(callers, 50) / 10.0)
        weighted += risk
        for name, rx in CONCERN:
            if rx.search(path):
                concerns.add(name)
        if is_test(path):
            test_churn += churn
        if is_sensitive(path):
            sensitive_churn += churn
        per_file.append({
            "path": path, "churn": churn, "criticality": crit,
            "callers_est": callers, "risk": round(risk, 1),
        })

    per_file.sort(key=lambda x: x["risk"], reverse=True)
    # normalize to 0-100 with a soft cap
    score = min(100, round(weighted / 60.0))

    flags = []
    if total_churn > TOO_BIG_CHURN or len(files) > TOO_BIG_FILES:
        flags.append({
            "flag": "too_big",
            "detail": f"{total_churn} lines across {len(files)} files — "
                      f"split for reliable review (thresholds {TOO_BIG_CHURN}/{TOO_BIG_FILES})."})
    code_concerns = concerns - {"docs"}
    if len(code_concerns) >= 4:
        flags.append({
            "flag": "mixed_concerns",
            "detail": f"touches {sorted(code_concerns)} — consider separating "
                      f"refactor / feature / migration / config into their own PRs."})
    if sensitive_churn > 0 and test_churn == 0:
        flags.append({
            "flag": "risky_no_tests",
            "detail": f"{sensitive_churn} lines changed in sensitive code with no test changes."})

    print(json.dumps({
        "score": score,
        "score_scale": "0 (trivial) .. 100 (review with extreme care / split)",
        "total_churn": total_churn,
        "files_changed": len(files),
        "concerns": sorted(concerns),
        "flags": flags,
        "top_files": per_file[:10],
    }, indent=2))


if __name__ == "__main__":
    main()
