"""Leak check for a commit: listed names, AI co-authorship, model traces, home paths, secrets.

Runs on staged changes and on commit or PR text, under a second. The list of names lives only
in the owner's local config, never in a repository.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

HASH_COMMENT = {".py", ".sh", ".bash", ".zsh", ".rb", ".yml", ".yaml", ".toml", ".cfg", ".ini"}
SLASH_COMMENT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".c"}
SLASH_COMMENT |= {".cc", ".cpp", ".h", ".hpp", ".rs", ".swift", ".cs", ".php", ".dart", ".scss"}
COAUTHOR = re.compile(
    r"co-authored-by:.*(claude|anthropic|openai|copilot|chatgpt)"
    r"|generated with \[?claude code|\U0001f916 generated",
    re.IGNORECASE,
)
TRACE_PHRASES = (
    r"as an ai\b",
    r"\blanguage model\b",
    r"\bi(?:'ve| have) (?:updated|added|changed|fixed|refactored|implemented|removed)\b",
    r"\bhere(?:'s| is) the (?:updated|fixed|new|refactored|corrected)\b",
    r"\b(?:as )?per your (?:request|instructions)\b",
    r"\byou asked\b",
)
MODEL_WORDS = ("claude", "anthropic", "chatgpt", "openai", "copilot", "gemini")
PLACEHOLDER_USERS = {"runner", "user", "username", "you", "me", "name", "example", "ubuntu"}
HOME_PATH = re.compile(r"/(?:home|Users)/([A-Za-z0-9._-]+)/")


class LeakCheckError(Exception):
    """The check could not run (no git, no gitleaks, unreadable diff)."""


@dataclass(frozen=True)
class Finding:
    """One leak: where, which rule, and an excerpt with the leaked part masked."""

    path: str
    line: int
    rule: str
    excerpt: str


def load_terms(path: Path) -> list[str]:
    """Read the private list of names: one per line, `#` starts a comment."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _mask(text: str, start: int, end: int) -> str:
    hidden = text[start] + "*" * (end - start - 1)
    excerpt = text[:start] + hidden + text[end:]
    return excerpt.strip()[:160]


def _term_pattern(terms: Iterable[str]) -> re.Pattern[str] | None:
    """Match listed names as whole words; `=Name` in the list matches only that exact case."""
    words = sorted({term for term in terms if term.lstrip("=")}, key=len, reverse=True)
    if not words:
        return None
    parts = [
        re.escape(word[1:]) if word.startswith("=") else f"(?i:{re.escape(word)})" for word in words
    ]
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


def _trace_pattern(allow: Iterable[str]) -> re.Pattern[str]:
    allowed = {word.lower() for word in allow}
    models = [rf"\b{word}\b" for word in MODEL_WORDS if word not in allowed]
    return re.compile("|".join([*TRACE_PHRASES, *models]), re.IGNORECASE)


def _comment(path: str, line: str) -> str | None:
    suffix = Path(path).suffix.lower()
    stripped = line.strip()
    markers: tuple[str, ...]
    if suffix in HASH_COMMENT:
        markers = ("#",)
    elif suffix in SLASH_COMMENT:
        markers = ("//", "/*", "*")
    elif suffix in {".md", ".txt", ".rst", ""}:
        return None
    else:
        markers = ("#", "//", "/*")
    for marker in markers:
        if stripped.startswith(marker):
            return stripped
        inline = f" {marker} " if marker != "*" else None
        if inline and inline in line:
            return line[line.index(inline) :]
    return None


def scan_line(
    path: str,
    number: int,
    text: str,
    terms: re.Pattern[str] | None,
    traces: re.Pattern[str],
) -> Iterator[Finding]:
    """Yield the leaks in one added line."""
    if terms and (match := terms.search(text)):
        yield Finding(path, number, "listed name", _mask(text, match.start(), match.end()))
    if COAUTHOR.search(text):
        yield Finding(path, number, "ai co-authorship", text.strip()[:160])
    for home in HOME_PATH.finditer(text):
        if home.group(1).lower() not in PLACEHOLDER_USERS:
            yield Finding(path, number, "home path", _mask(text, home.start(1), home.end(1)))
            break
    comment = _comment(path, text)
    if comment and traces.search(comment):
        yield Finding(path, number, "model trace", text.strip()[:160])


def scan_diff(diff: str, terms: Iterable[str], allow: Iterable[str] = ()) -> list[Finding]:
    """Scan the added lines of a unified diff."""
    term_re, trace_re = _term_pattern(terms), _trace_pattern(allow)
    found: list[Finding] = []
    path, number, previous = "", 0, ""
    for line in diff.splitlines():
        header = previous.startswith("--- ")
        previous = line
        if header and line.startswith("+++ "):
            target = line[4:]
            path = "" if target == "/dev/null" else target.removeprefix("b/")
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            number = int(match.group(1)) if match else 0
        elif line.startswith("+") and path:
            found.extend(scan_line(path, number, line[1:], term_re, trace_re))
            number += 1
    return found


def scan_text(text: str, terms: Iterable[str]) -> list[Finding]:
    """Scan a commit message or PR text: names, co-authorship, home paths."""
    term_re = _term_pattern(terms)
    found: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for finding in scan_line("message", number, line, term_re, re.compile(r"(?!x)x")):
            found.append(finding)
    return found


def _gitleaks(repo: Path, which: Callable[[str], str | None]) -> list[Finding]:
    if which("gitleaks") is None:
        raise LeakCheckError("gitleaks is not installed; the secret scan cannot run")
    completed = subprocess.run(
        [
            *("gitleaks", "git", "--staged", "--pre-commit", "--redact", "--no-banner"),
            *("--report-format", "json", "--report-path", "-", "--exit-code", "3", str(repo)),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in (0, 3):
        raise LeakCheckError(f"gitleaks failed: {completed.stderr.strip()[-300:]}")
    try:
        reports = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as error:
        raise LeakCheckError(f"gitleaks output is not JSON: {error.msg}") from error
    return [
        Finding(r.get("File", "?"), int(r.get("StartLine", 0)), "secret", r.get("RuleID", "?"))
        for r in reports
    ]


def check_staged(
    repo: Path,
    terms: Iterable[str],
    *,
    allow: Iterable[str] = (),
    gitleaks: bool = True,
    which: Callable[[str], str | None] = shutil.which,
) -> list[Finding]:
    """Check what is staged in `repo`; raise LeakCheckError when a scan cannot run."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "diff", "--cached", "-U0", "--no-color", "--no-ext-diff"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise LeakCheckError("git is not installed") from error
    if completed.returncode != 0:
        raise LeakCheckError(f"git diff failed: {completed.stderr.strip()}")
    found = scan_diff(completed.stdout, terms, allow)
    if gitleaks:
        found += _gitleaks(repo, which)
    return found


def report(repo: Path, terms: list[str], settings: dict, message: str | None = None) -> list[str]:
    """Check the staged change and message under a project's `leaks` settings; one line each.

    Ignore globs cover a checker's own fixtures; a secret found by gitleaks is never ignored.
    """
    allow = list(settings.get("allow", []))
    # A word allowed here (the owner's public handle in his own plugin) is no leak in this repo.
    allowed = {word.lower() for word in allow}
    terms = [term for term in terms if term.lstrip("=").lower() not in allowed]
    found = check_staged(repo, terms, allow=allow, gitleaks=settings.get("gitleaks", True))
    if message:
        found += scan_text(message, terms)
    ignore = list(settings.get("ignore", []))
    return [
        f"{f.path}:{f.line}: {f.rule}: {f.excerpt}"
        for f in found
        if f.rule == "secret" or not any(fnmatch.fnmatch(f.path, glob) for glob in ignore)
    ]
