"""The machine map of a repository (D029): where symbols are defined and called.

Freshness comes from a hash over every mapped file. Edges are leads to read, never facts, and
a stale map is never served as fact.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from .codecheck import CODE

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
SKIP_DIRS |= {".next", ".tox", "target", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
DEFS = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?|class|def|func|fn|interface|type)"
    r"\s+([A-Za-z_$][\w$]*)"
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(|function)",
    re.MULTILINE,
)
CALLS = re.compile(r"([A-Za-z_$][\w$]*)\s*\(")
KEYWORDS = {"if", "for", "while", "switch", "return", "function", "catch", "typeof", "new"}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )


def _sources(root: Path) -> list[str]:
    listed = _git(root, "ls-files", "--cached", "--others", "--exclude-standard")
    if listed.returncode == 0:
        names = listed.stdout.splitlines()
    else:
        names = [
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file() and not SKIP_DIRS & set(p.relative_to(root).parts)
        ]
    return sorted(n for n in names if PurePosixPath(n).suffix in CODE and (root / n).is_file())


def _python(source: str) -> tuple[str, list[str], list[str]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "py-parse-error", [], []
    defs, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defs.add(node.name)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name:
                calls.add(name)
    return "py", sorted(defs), sorted(calls)


def _other(source: str, suffix: str) -> tuple[str, list[str], list[str]]:
    defs = {a or b for a, b in DEFS.findall(source)}
    calls = set(CALLS.findall(source)) - KEYWORDS - defs
    return suffix.lstrip("."), sorted(defs), sorted(calls)


def _record(root: Path, name: str, previous: dict[str, Any]) -> dict[str, Any]:
    data = (root / name).read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:16]
    if previous.get("hash") == digest:
        return previous
    source = data.decode("utf-8", errors="replace")
    suffix = PurePosixPath(name).suffix
    lang, defs, calls = _python(source) if suffix == ".py" else _other(source, suffix)
    return {"hash": digest, "lang": lang, "defs": defs, "calls": calls}


def _tree_hash(files: dict[str, dict[str, Any]]) -> str:
    joined = "\n".join(f"{name}\0{record['hash']}" for name, record in sorted(files.items()))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def store(state_dir: Path, root: Path) -> Path:
    """Where a repository's map lives: in bedrock's state, never inside the repository."""
    key = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:12]
    return state_dir / "maps" / f"{root.name}-{key}.json"


def build(root: Path, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the map; files whose hash did not change reuse their previous record."""
    old = (previous or {}).get("files", {})
    files = {name: _record(root, name, old.get(name, {})) for name in _sources(root)}
    symbols: dict[str, list[str]] = {}
    callers: dict[str, list[str]] = {}
    for name, record in files.items():
        for symbol in record["defs"]:
            symbols.setdefault(symbol, []).append(name)
        for symbol in record["calls"]:
            callers.setdefault(symbol, []).append(name)
    head = _git(root, "rev-parse", "HEAD")
    dirty = _git(root, "status", "--porcelain")
    return {
        "version": 1,
        "root": str(root),
        "stamp": {
            "git_head": head.stdout.strip() if head.returncode == 0 else None,
            "git_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
            "tree_hash": _tree_hash(files),
            "file_count": len(files),
        },
        "files": files,
        "symbols": symbols,
        "callers": {k: v for k, v in callers.items() if k in symbols},
    }


def write(target: Path, data: dict[str, Any]) -> Path:
    """Store the map atomically, so a reader never sees half a file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    temporary.replace(target)
    return target


def load(target: Path) -> dict[str, Any] | None:
    """The stored map, or None when there is none or it is unreadable."""
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def check(root: Path, target: Path) -> str:
    """Return `fresh`, `stale` or `absent` by re-hashing the mapped files (no parsing)."""
    stored = load(target)
    if stored is None:
        return "absent"
    hashes = {}
    for name in _sources(root):
        hashes[name] = {"hash": hashlib.sha256((root / name).read_bytes()).hexdigest()[:16]}
    return "fresh" if _tree_hash(hashes) == stored["stamp"]["tree_hash"] else "stale"
