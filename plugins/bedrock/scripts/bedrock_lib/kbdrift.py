"""Module notes against the code: which notes went stale since the commit they were verified at.

A note is stale when a file under its `covers` changed since `verified_at`; with `anchors`, only
when a change touches one of the named symbols (D026).
"""

from __future__ import annotations

import ast
import re
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any

from .codemap import DEFS
from .kb import Note, all_notes, covers, empty, under

DRIFT_BUDGET_SECONDS = 5.0


class _OutOfTime(Exception):
    """The drift budget ran out in the middle of a note."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    argv = ["git", "-C", str(repo), *args]
    try:
        return subprocess.run(argv, capture_output=True, text=True, check=False, timeout=30)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", "git timed out")


def _names(output: str) -> list[str]:
    return [name for name in output.split("\0") if name]


def _spans(source: str, suffix: str, names: list[str]) -> list[tuple[int, int]]:
    """Line ranges of the named symbols: exact for Python, from one definition to the next else."""
    if suffix == ".py":
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        return [
            (node.lineno, node.end_lineno or node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name in names
        ]
    starts = [
        (source.count("\n", 0, match.start()) + 1, next(g for g in match.groups() if g))
        for match in DEFS.finditer(source)
    ]
    lines = source.count("\n") + 1
    return [
        (line, (starts[i + 1][0] - 1) if i + 1 < len(starts) else lines)
        for i, (line, name) in enumerate(starts)
        if name in names
    ]


def _hunks(repo: Path, commit: str, path: str) -> list[tuple[int, int, int, int]]:
    patch = _git(
        repo, "diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames",
        "--end-of-options", commit, "HEAD", "--", path,
    ).stdout  # fmt: skip
    found = []
    for match in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", patch, re.M):
        old, old_n, new, new_n = match.groups()
        found.append((int(old), int(old_n or 1), int(new), int(new_n or 1)))
    return found


def _anchored_change(repo: Path, commit: str, path: str, anchors: list[str]) -> bool:
    suffix = PurePosixPath(path).suffix
    before = _git(repo, "show", f"{commit}:{path}").stdout
    after = _git(repo, "show", f"HEAD:{path}").stdout
    old_spans, new_spans = _spans(before, suffix, anchors), _spans(after, suffix, anchors)
    for old, old_n, new, new_n in _hunks(repo, commit, path):
        # A side with no lines only marks where the other side's lines go: it touches nothing.
        if old_n and any(a < old + old_n and old <= b for a, b in old_spans):
            return True
        if new_n and any(a < new + new_n and new <= b for a, b in new_spans):
            return True
    return False


def _tree(repo: Path, commit: str) -> set[str] | None:
    listed = _git(repo, "ls-tree", "-r", "-z", "--name-only", "--end-of-options", commit)
    return set(_names(listed.stdout)) if listed.returncode == 0 else None


def _anchors(note: Note) -> list[str]:
    value = note.meta.get("anchors") or []
    items = value if isinstance(value, list) else [value]
    return [str(item) for item in items if str(item).strip() and not empty(item)]


def _note_drift(
    repo: Path, note: Note, commit: str, cache: dict[str, Any], deadline: float
) -> str | None:
    if commit not in cache:
        changed = _git(
            repo, "diff", "--name-only", "-z", "--no-renames", "--end-of-options", commit, "HEAD"
        )
        cache[commit] = (changed.returncode, _names(changed.stdout), _tree(repo, commit))
    code, changed, old_tree = cache[commit]
    if code != 0:
        return f"note {note.name}: git could not compare {commit[:10]} with HEAD"
    head = cache.setdefault("HEAD-tree", _tree(repo, "HEAD")) or set()
    known = head | (old_tree or set())
    missing = [c for c in covers(note) if not any(under(p, c) for p in known)]
    if missing:
        return f"note {note.name}: covered path {', '.join(missing)} does not exist in the code"
    files = [p for p in changed if any(under(p, c) for c in covers(note))]
    if files and (anchors := _anchors(note)):
        kept = []
        for path in files:
            if time.monotonic() > deadline:
                raise _OutOfTime
            if _anchored_change(repo, commit, path, anchors):
                kept.append(path)
        files = kept
    if files:
        return (
            f"note {note.name} is stale: {', '.join(files)} changed since {commit[:10]}; "
            "update § Boundaries/Rules or record that nothing changes and why (D026)"
        )
    return None


def drift(bank: Path, project: str, repo: Path, budget: float = DRIFT_BUDGET_SECONDS) -> list[str]:
    """List module notes whose covered code changed since the commit they were verified at."""
    started = time.monotonic()
    deadline = started + budget
    found: list[str] = []
    cache: dict[str, Any] = {}
    modules = [n for n in all_notes(bank, project) if n.meta.get("type") == "module"]
    for index, note in enumerate(modules):
        if time.monotonic() > deadline:
            found.append(f"drift truncated after {index} of {len(modules)} notes (time budget)")
            break
        if not covers(note):
            continue
        commit = str(note.meta.get("verified_at", ""))
        if not commit or _git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            found.append(f"note {note.name}: verified_at {commit!r} is an unknown commit")
            continue
        try:
            message = _note_drift(repo, note, commit, cache, deadline)
        except _OutOfTime:
            found.append(f"drift truncated inside note {note.name} (time budget)")
            break
        if message:
            found.append(message)
    return found
