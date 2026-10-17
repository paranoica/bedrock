"""Read one change from git: staged, or HEAD against a base; added and removed lines per file."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class CheckError(Exception):
    """A check could not run (git failed, the registry is unreachable)."""


@dataclass
class Change:
    """One changed file: status, added and removed lines, old and new text."""

    path: str
    status: str
    added: list[tuple[int, str]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    old: str | None = None
    new: str | None = None


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise CheckError(f"git {' '.join(args[:2])} failed: {done.stderr.strip()}")
    return done.stdout


def git_root(start: Path) -> str:
    """Return the top folder of the git repository holding `start`."""
    return _git(start, "rev-parse", "--show-toplevel").strip()


def _show(repo: Path, spec: str) -> str | None:
    done = subprocess.run(
        ["git", "-C", str(repo), "show", spec], capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else None


def _revisions(repo: Path, base: str | None) -> tuple[list[str], str, str]:
    """Return the diff range arguments and the specs of the old and new trees."""
    if base is None:
        return ["--cached"], "HEAD", ""
    merge_base = _git(repo, "merge-base", base, "HEAD").strip()
    return [merge_base, "HEAD"], merge_base, "HEAD"


def changes(repo: Path, base: str | None = None) -> list[Change]:
    """Collect the changed files of the staged change, or of HEAD against `base`."""
    revisions, old_rev, new_rev = _revisions(repo, base)
    found: dict[str, Change] = {}
    for line in _git(repo, "diff", *revisions, "--name-status", "--no-renames").splitlines():
        status, _, path = line.partition("\t")
        found[path] = Change(path, status[:1])
    patch = _git(repo, "diff", *revisions, "-U0", "--no-color", "--no-renames", "--no-ext-diff")
    _read_patch(patch, found)
    for change in found.values():
        if change.status != "A":
            change.old = _show(repo, f"{old_rev}:{change.path}")
        if change.status != "D":
            change.new = _show(repo, f"{new_rev}:{change.path}")
    return list(found.values())


def _read_patch(patch: str, found: dict[str, Change]) -> None:
    current: Change | None = None
    number = 0
    previous = ""
    for line in patch.splitlines():
        header = previous.startswith("--- ")
        previous = line
        if header and line.startswith("+++ "):
            current = found.get(line[4:].removeprefix("b/"))
        elif line.startswith("--- ") and not header:
            continue
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            number = int(match.group(1)) if match else 0
        elif current is not None and line.startswith("+"):
            current.added.append((number, line[1:]))
            number += 1
        elif current is not None and line.startswith("-"):
            current.removed.append(line[1:])


def deleted_paths(repo: Path, base: str | None) -> list[str]:
    """Return the files the change deletes."""
    revisions, _, _ = _revisions(repo, base)
    listing = _git(repo, "diff", *revisions, "--name-status", "--no-renames")
    return [line.split("\t", 1)[1] for line in listing.splitlines() if line.startswith("D")]
