#!/usr/bin/env python3
"""
Check dependencies against OSV.dev for known vulnerabilities.

Reads lockfiles under the target dir:
- package-lock.json, pnpm-lock.yaml, yarn.lock (npm/Node)
- poetry.lock, Pipfile.lock, requirements.txt (Python)

Strategy:
  1. Parse lockfiles -> normalized (ecosystem, name, version) tuples.
  2. Fast pass: POST batches to /v1/querybatch (1 request per 100 deps) to find
     which deps have ANY advisory. Most deps are clean, so this is cheap.
  3. Detail pass: for the (usually few) flagged deps, GET full advisory via
     /v1/query and compute a real CVSS severity. Cached per (eco,name,ver) 24h.

Outputs JSON to stdout. Severity is computed from the CVSS vector when present,
NOT guessed — UNKNOWN only when OSV ships no scorable severity.

Usage: python3 check_cves.py [path]
"""

import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE_DIR = Path(os.environ.get("CLAUDE_CACHE_DIR", ".claude/cache"))
CACHE_TTL = 24 * 60 * 60
OSV_QUERY = "https://api.osv.dev/v1/query"
OSV_BATCH = "https://api.osv.dev/v1/querybatch"
TIMEOUT = 15
MAX_DEPS = 1500            # overall cap
BATCH_SIZE = 100           # OSV querybatch chunk
UA = {"User-Agent": "code-review-skill/2.1.1 (+osv.dev)"}


# ----------------------------- CVSS v3.1 -----------------------------
# Compute a real base score from the vector instead of faking the band.
def cvss31_base(vector: str):
    try:
        parts = dict(p.split(":", 1) for p in vector.split("/") if ":" in p)
    except ValueError:
        return None
    if "AV" not in parts:
        return None
    AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}.get(parts.get("AV"))
    AC = {"L": 0.77, "H": 0.44}.get(parts.get("AC"))
    UI = {"N": 0.85, "R": 0.62}.get(parts.get("UI"))
    scope_changed = parts.get("S") == "C"
    pr_map = ({"N": 0.85, "L": 0.68, "H": 0.5} if scope_changed
              else {"N": 0.85, "L": 0.62, "H": 0.27})
    PR = pr_map.get(parts.get("PR"))
    imp = {"H": 0.56, "L": 0.22, "N": 0.0}
    C, I, A = imp.get(parts.get("C")), imp.get(parts.get("I")), imp.get(parts.get("A"))
    if None in (AV, AC, UI, PR, C, I, A):
        return None
    isc_base = 1 - (1 - C) * (1 - I) * (1 - A)
    if scope_changed:
        impact = 7.52 * (isc_base - 0.029) - 3.25 * (isc_base - 0.02) ** 15
    else:
        impact = 6.42 * isc_base
    if impact <= 0:
        return 0.0
    expl = 8.22 * AV * AC * PR * UI
    raw = min((1.08 if scope_changed else 1.0) * (impact + expl), 10.0)
    # CVSS 3.1 roundup
    i = int(round(raw * 100000))
    score = (i / 100000) if i % 10000 == 0 else (math.floor(i / 10000) / 10.0 + 0.1)
    return round(score, 1)


def band(score):
    if score is None:
        return "UNKNOWN"
    if score == 0:
        return "NONE"
    if score < 4.0:
        return "LOW"
    if score < 7.0:
        return "MEDIUM"
    if score < 9.0:
        return "HIGH"
    return "CRITICAL"


def _cvss_vectors(vuln: dict):
    """Yield (version, vector) for every CVSS vector on the advisory or its
    affected[] entries. Keys off the SCORE-STRING prefix, never the `type` field:
    OSV sometimes ships type as the integer 3 instead of "CVSS_V4" (osv.dev#2335),
    so trusting `type` silently drops v4 vectors."""
    out = []

    def scan(arr):
        for s in arr or []:
            sc = s.get("score", "")
            if isinstance(sc, str) and sc.startswith("CVSS:"):
                ver = sc.split("/", 1)[0].split(":", 1)[-1]   # '4.0' / '3.1' / '3.0'
                out.append((ver, sc))

    scan(vuln.get("severity"))
    for aff in vuln.get("affected") or []:
        scan(aff.get("severity"))
    return out


def cvss4_base(vector: str):
    """CVSS 4.0 base is a MacroVector table lookup, not a closed form — and OSV
    ships the v4 vector but NOT a computed score (osv.dev#2643). We do NOT fake a
    v4 score: use the optional `cvss` lib if the host has it, else return None and
    let the caller fall back honestly."""
    try:
        from cvss import CVSS4  # optional; skill stays zero-dependency without it
    except Exception:
        return None
    try:
        return round(float(CVSS4(vector).base_score), 1)
    except Exception:
        return None


def assess_severity(vuln: dict):
    """Return (band, source, vector_or_None).

    Order of trust: CVSS 4.0 (current standard, if scorable) -> CVSS 3.x closed-form
    (always computable offline) -> ecosystem text severity (GHSA ships it). If a CVSS
    vector EXISTS but none of those could score it (v4-only, no `cvss` lib, no text),
    we return band "REVIEW" — NOT "UNKNOWN" — so an unscored-but-real advisory is
    surfaced for manual scoring and never silently treated as clean. `vector` is
    always carried out so the reviewer can score it by hand."""
    vectors = _cvss_vectors(vuln)
    v4 = next((vec for ver, vec in vectors if ver.startswith("4")), None)
    v3 = next((vec for ver, vec in vectors if ver.startswith("3")), None)

    if v4:
        b = band(cvss4_base(v4))
        if b != "UNKNOWN":
            return b, "cvss4", v4
    if v3:
        b = band(cvss31_base(v3))
        if b != "UNKNOWN":
            return b, "cvss3", v3

    ds = vuln.get("database_specific") or {}
    txt = ds.get("severity")
    if isinstance(txt, str) and txt:
        return txt.upper(), "text", (v4 or v3)

    if vectors:
        # there is a real CVSS vector we couldn't score offline — flag, don't bury
        return "REVIEW", "unscored-vector", (v4 or v3)
    return "UNKNOWN", "none", None


def severity_of(vuln: dict) -> str:
    """Back-compat thin wrapper: band only."""
    return assess_severity(vuln)[0]


# ----------------------------- normalization -----------------------------
def norm_pypi(name: str) -> str:
    # PEP 503: lowercase, collapse runs of -, _, . into a single -
    return re.sub(r"[-_.]+", "-", name).lower()


def norm_npm(name: str) -> str:
    return name.lower()  # npm registry is case-insensitive/lowercased


def normalize(eco: str, name: str, version: str):
    name = name.strip()
    version = version.strip().lstrip("=v").split("(")[0].strip()
    if not name or not version:
        return None
    if eco == "PyPI":
        return ("PyPI", norm_pypi(name), version)
    return ("npm", norm_npm(name), version)


# ----------------------------- lockfile parsers -----------------------------
def parse_package_lock_json(path: Path):
    data = json.loads(path.read_text())
    deps = []
    for key, info in (data.get("packages") or {}).items():
        if not key:
            continue
        if info.get("link"):                       # workspace symlink, not a registry pkg
            continue
        resolved = info.get("resolved") or ""
        if resolved.startswith("file:") or resolved.startswith("link:"):
            continue
        # Registry deps live under node_modules/. Keys without it (root "",
        # workspace paths like "apps/web") are local code, not deps — skip them.
        if "node_modules/" not in key:
            continue
        name = key.split("node_modules/")[-1]
        version = info.get("version")
        if name and version:
            deps.append(("npm", name, version))
    # fall back to legacy v1 "dependencies" tree
    if not deps:
        def walk(d):
            for n, meta in (d or {}).items():
                v = meta.get("version")
                if v:
                    deps.append(("npm", n, v))
                walk(meta.get("dependencies"))
        walk(data.get("dependencies"))
    return deps


def parse_pnpm_lock(path: Path):
    """Handle pnpm lockfileVersion 5.x, 6.0 and 9.0 key shapes."""
    deps = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # strip an optional leading slash (v5/v6) and surrounding quotes (v9)
        key = line.rstrip(":").strip().strip("'\"")
        if key.startswith("/"):
            key = key[1:]
        # v9 / v6: name@version            (scoped: @scope/name@version)
        m = re.match(r"^((?:@[^/@\s]+/)?[^@/\s][^@\s]*)@([0-9][^():\s]*)$", key)
        if m:
            deps.append(("npm", m.group(1), m.group(2)))
            continue
        # v5: name/version                 (scoped: @scope/name/version)
        m = re.match(r"^((?:@[^/@\s]+/)?[^@/\s][^/\s]*)/([0-9][^():\s/]*)$", key)
        if m:
            deps.append(("npm", m.group(1), m.group(2)))
    return deps


def parse_yarn_lock(path: Path):
    """Handle yarn classic (v1) and Berry (v2+) YAML-ish lockfiles."""
    deps = []
    content = path.read_text()
    current = None
    for raw in content.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw[0].isspace():                   # header line
            head = raw.split(":", 1)[0]
            first = head.split(",")[0].strip().strip('"')
            # strip the @range / @npm:range suffix, keep the (possibly scoped) name
            m = re.match(r"^((?:@[^/]+/)?[^@]+)@", first)
            current = m.group(1) if m else None
        else:
            v = re.match(r'^\s+version:?\s+"?([^"\s]+)"?', raw)  # quoted (v1) or bare (Berry)
            if v and current:
                deps.append(("npm", current, v.group(1)))
                current = None
    return deps


def parse_poetry_lock(path: Path):
    deps = []
    blocks = re.split(r"^\[\[package\]\]\s*$", path.read_text(), flags=re.MULTILINE)
    for block in blocks[1:]:
        n = re.search(r'^name\s*=\s*"([^"]+)"', block, re.MULTILINE)
        v = re.search(r'^version\s*=\s*"([^"]+)"', block, re.MULTILINE)
        if n and v:
            deps.append(("PyPI", n.group(1), v.group(1)))
    return deps


def parse_pipfile_lock(path: Path):
    deps = []
    data = json.loads(path.read_text())
    for section in ("default", "develop"):
        for name, info in (data.get(section) or {}).items():
            ver = (info.get("version") or "").lstrip("=")
            if ver:
                deps.append(("PyPI", name, ver))
    return deps


def parse_requirements_txt(path: Path):
    deps = []
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-") or line.startswith("git+"):
            continue
        # name, optional [extras], == version
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9_.\-+!]+)", line)
        if m:
            deps.append(("PyPI", m.group(1), m.group(2)))
    return deps


PARSERS = [
    ("package-lock.json", parse_package_lock_json),
    ("pnpm-lock.yaml", parse_pnpm_lock),
    ("yarn.lock", parse_yarn_lock),
    ("poetry.lock", parse_poetry_lock),
    ("Pipfile.lock", parse_pipfile_lock),
    ("requirements.txt", parse_requirements_txt),
]

SKIP_DIRS = {"node_modules", ".venv", "venv", "dist", "build", ".next", ".git"}


def find_and_parse(root: Path):
    by_eco = {"npm": [], "PyPI": []}
    errors, files_seen = [], []
    for filename, parser in PARSERS:
        for path in root.rglob(filename):
            if any(p in SKIP_DIRS for p in path.parts):
                continue
            files_seen.append(str(path.relative_to(root)))
            try:
                for eco, name, ver in parser(path):
                    n = normalize(eco, name, ver)
                    if n:
                        by_eco[n[0]].append(n)
            except Exception as e:
                errors.append(f"{path}: {e}")
    # dedupe per ecosystem
    for eco in by_eco:
        by_eco[eco] = sorted(set(by_eco[eco]))
    return by_eco, files_seen, errors


def balanced_cap(by_eco):
    """Interleave ecosystems so a big npm tree can't starve Python deps."""
    pools = [list(v) for v in by_eco.values() if v]
    out, i = [], 0
    while pools and len(out) < MAX_DEPS:
        pool = pools[i % len(pools)]
        if pool:
            out.append(pool.pop(0))
        if not pool:
            pools.remove(pool)
            i -= 1
        i += 1
    return out


# ----------------------------- OSV calls -----------------------------
def cache_path(dep):
    h = hashlib.sha256((":".join(dep)).encode()).hexdigest()[:16]
    return CACHE_DIR / f"osv-{h}.json"


def cached(dep):
    p = cache_path(dep)
    if p.exists() and (time.time() - p.stat().st_mtime) <= CACHE_TTL:
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def write_cache(dep, payload):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(dep).write_text(json.dumps(payload))


def _post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def batch_flag(deps, errors):
    """Return the subset of deps that OSV reports as having >=1 advisory."""
    flagged = []
    for i in range(0, len(deps), BATCH_SIZE):
        chunk = deps[i:i + BATCH_SIZE]
        queries = [{"package": {"name": n, "ecosystem": e}, "version": v}
                   for (e, n, v) in chunk]
        try:
            res = _post(OSV_BATCH, {"queries": queries}).get("results", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            errors.append(f"batch {i//BATCH_SIZE}: {e}")
            flagged.extend(chunk)          # degrade: detail-check the whole chunk
            continue
        for dep, r in zip(chunk, res):
            if r and r.get("vulns"):
                flagged.append(dep)
        time.sleep(0.05)
    return flagged


def detail(dep, errors):
    c = cached(dep)
    if c is not None:
        return c, True
    eco, name, ver = dep
    try:
        data = _post(OSV_QUERY, {"package": {"name": name, "ecosystem": eco}, "version": ver})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        errors.append(f"{eco}:{name}@{ver}: {e}")
        return None, False
    write_cache(dep, data)
    time.sleep(0.05)
    return data, False


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    by_eco, files_seen, parse_errors = find_and_parse(root)
    total = sum(len(v) for v in by_eco.values())
    deps = balanced_cap(by_eco)

    result = {
        "lockfiles_found": files_seen,
        "deps_total": total,
        "deps_scanned": len(deps),
        "vulnerable": [],
        "errors": list(parse_errors),
    }
    if total > len(deps):
        result["errors"].append(
            f"{total} deps found; scanned {len(deps)} (balanced cap {MAX_DEPS}).")
    if not deps:
        result["errors"].append("No lockfile dependencies parsed.")
        print(json.dumps(result, indent=2))
        return

    flagged = batch_flag(deps, result["errors"])
    result["flagged_by_batch"] = len(flagged)

    for dep in flagged:
        data, _ = detail(dep, result["errors"])
        if not data:
            continue
        vulns = data.get("vulns") or []
        if not vulns:
            continue
        eco, name, ver = dep
        def _adv(v):
            band_, src, vec = assess_severity(v)
            return {
                "id": v.get("id"),
                "summary": (v.get("summary") or "")[:200],
                "severity": band_,
                "severity_source": src,        # cvss4 | cvss3 | text | unscored-vector | none
                "cvss_vector": vec,            # carried so REVIEW rows can be scored by hand
                "aliases": v.get("aliases", []),
                "fixed": _fixed_versions(v, eco, name),
            }
        advisories = [_adv(v) for v in vulns]
        # CVE rows sort to the top of the report; expose worst severity for ordering.
        # REVIEW (real vector we couldn't score offline) sorts ABOVE MEDIUM so it
        # can't hide — it means "score this manually", not "low risk".
        order = {"CRITICAL": 5, "HIGH": 4, "REVIEW": 3, "MEDIUM": 2, "LOW": 1}
        worst = max((a["severity"] for a in advisories),
                    key=lambda s: order.get(s, 0), default="UNKNOWN")
        result["vulnerable"].append({
            "ecosystem": eco, "package": name, "version": ver,
            "worst_severity": worst, "advisories": advisories,
        })

    order = {"CRITICAL": 5, "HIGH": 4, "REVIEW": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0, "NONE": 0}
    result["vulnerable"].sort(key=lambda x: order.get(x["worst_severity"], 0), reverse=True)
    print(json.dumps(result, indent=2))


def _fixed_versions(vuln, eco, name):
    fixed = []
    for aff in vuln.get("affected") or []:
        pkg = aff.get("package") or {}
        if pkg.get("name", "").lower() not in (name.lower(),):
            continue
        for rng in aff.get("ranges") or []:
            for ev in rng.get("events") or []:
                if "fixed" in ev:
                    fixed.append(ev["fixed"])
    return sorted(set(fixed))


if __name__ == "__main__":
    main()
