"""Code checks on a change (D022): the rules a reviewer should not have to remember.

Exit-code contract of the command: 0 clean, 1 a violation, 2 the check could not run.
Duplicates, dead code and import contracts need per-language tools and are not done here.
"""

from __future__ import annotations

import ast
import fnmatch
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from . import packages
from .gitdiff import Change, changes, deleted_paths
from .gitdiff import CheckError as CheckError
from .gitdiff import git_root as git_root

CODE = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".rb"}
CODE |= {".rs", ".swift", ".cs", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".dart", ".sh"}
DUMP_NAMES = {"utils", "util", "helpers", "helper", "misc", "common", "commons"}
TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$"
)
CONFIG_PATH = re.compile(
    r"(^|/)(config|configs|settings|\.github)/|\.(json|ya?ml|toml|ini|env\w*)$"
)
# (pattern in the comment, pattern in the code before the comment, comment marker)
PY_ESCAPE = (re.compile(r"\btype:\s*ignore"), re.compile(r"\bcast\("), "#")
TS_ESCAPE = (
    re.compile(r"@ts-(ignore|expect-error)"),
    re.compile(r"\bas any\b|:\s*any\b|<any>|\bany\[\]"),
    "//",
)
TS_SUFFIXES = {".ts", ".tsx", ".mts", ".cts"}
ASSERTION = re.compile(r"\bassert\b|\bexpect\(|\.assert\w*\(|\.should\b")
SKIP_OR_ONLY = re.compile(
    r"@pytest\.mark\.skip|\bpytest\.skip\(|@unittest\.skip"
    r"|\b(it|test|describe)\.(skip|only)\(|\bx(it|describe|test)\(|\bf(it|describe)\("
)
PY_PATCH = re.compile(r"""patch(?:\.object)?\(\s*["']([A-Za-z_][\w.]*)""")
JS_MOCK = re.compile(r"""\b(?:jest|vi)\.mock\(\s*["'](\.{1,2}/|@/|~/|src/)""")
URL = re.compile(r"""https?://([^/\s"'`]+)""")
IP = re.compile(r"""["'`]((?:\d{1,3}\.){3}\d{1,3})(?::\d+)?["'`]""")
SAFE_HOSTS = ("example.com", "example.org", "example.net", "www.w3.org", "json-schema.org")
SQL = r"\b(?:SELECT|INSERT|UPDATE|DELETE)\b"
RAW_SQL = re.compile(
    rf"""\bf["'][^"']*{SQL}[^"']*\{{"""
    rf"""|`[^`]*{SQL}[^`]*\$\{{"""
    rf"""|["'][^"']*{SQL}[^"']*["']\s*(?:\+|%\s*[(\w]|\.format\()"""
)
DEBUG = re.compile(
    r"\bconsole\.(log|debug)\(|^\s*debugger;?\s*$|\bbreakpoint\(\)|\bpdb\.set_trace\("
)
COMMIT = re.compile(r"(feat|fix|refactor|docs|test|chore|ci)(\([a-z0-9._-]+\))?: \S.*")
NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
MIN_AGE_DAYS = 90
MIN_WEEKLY_DOWNLOADS = 1000


@dataclass(frozen=True)
class Finding:
    """One violation: where, which check, and what is wrong."""

    path: str
    line: int
    check: str
    message: str


@dataclass(frozen=True)
class Limits:
    """Size limits; existing files and functions over them may not grow."""

    file_lines: int = 400
    function_lines: int = 60


def is_test(path: str) -> bool:
    """Return True for a test file in any of the usual layouts."""
    return bool(TEST_PATH.search(path))


def is_code(path: str) -> bool:
    """Return True for a source file in a language the checks know."""
    return PurePosixPath(path).suffix.lower() in CODE


def _functions(source: str | None) -> dict[str, tuple[int, int]]:
    if source is None:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    sizes: dict[str, tuple[int, int]] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                name = f"{prefix}{child.name}"
                if not isinstance(child, ast.ClassDef):
                    end = child.end_lineno or child.lineno
                    sizes[name] = (child.lineno, end - child.lineno + 1)
                walk(child, name + ".")

    walk(tree, "")
    return sizes


def check_size(change: Change, limits: Limits) -> Iterator[Finding]:
    """New files and functions stay in limits; ones already over may not grow."""
    if change.new is None or not is_code(change.path):
        return
    new_count = change.new.count("\n")
    old_count = change.old.count("\n") if change.old is not None else None
    over = new_count > limits.file_lines and (old_count is None or new_count > old_count)
    if over and not is_test(change.path):
        message = f"{new_count} lines, limit {limits.file_lines}"
        yield Finding(change.path, 1, "size", message)
    if not change.path.endswith(".py"):
        return
    old_functions = _functions(change.old)
    for name, (line, length) in _functions(change.new).items():
        previous = old_functions.get(name, (0, 0))[1]
        if length > limits.function_lines and length > previous:
            message = f"function {name} is {length} lines, limit {limits.function_lines}"
            yield Finding(change.path, line, "size", message)


def check_dump_name(change: Change) -> Iterator[Finding]:
    """No new `utils`, `helpers`, `misc`, `common` modules or folders."""
    if change.status != "A":
        return
    parts = PurePosixPath(change.path).parts
    names = [PurePosixPath(part).stem.lower() for part in parts]
    if dump := next((name for name in names if name in DUMP_NAMES), None):
        yield Finding(change.path, 1, "dump name", f"'{dump}' says nothing about what it holds")


def check_type_escape(change: Change) -> Iterator[Finding]:
    """A type escape needs a FIXME(reason) on its line or the line above."""
    suffix = PurePosixPath(change.path).suffix.lower()
    rules = PY_ESCAPE if suffix == ".py" else TS_ESCAPE if suffix in TS_SUFFIXES else None
    if rules is None:
        return
    in_comment, in_code, marker = rules
    previous = ""
    for number, text in change.added:
        code, _, comment = text.partition(marker)
        escaped = in_comment.search(comment) or in_code.search(code)
        if escaped and "FIXME(" not in text and "FIXME(" not in previous:
            yield Finding(
                change.path, number, "type escape", "needs FIXME(reason): " + text.strip()
            )
        previous = text


def _assertion(text: str) -> str | None:
    match = ASSERTION.search(text)
    return text[match.start() :].strip() if match else None


def check_test_tampering(change: Change) -> Iterator[Finding]:
    """Flag removed assertions and new skips or onlys in test files."""
    if not is_test(change.path):
        return
    kept = {_assertion(text) for _, text in change.added} - {None}
    for text in change.removed:
        fragment = _assertion(text)
        if fragment is not None and fragment not in kept:
            yield Finding(change.path, 0, "test tampering", f"assertion removed: {text.strip()}")
    for number, text in change.added:
        if SKIP_OR_ONLY.search(text):
            message = f"skip or only added: {text.strip()}"
            yield Finding(change.path, number, "test tampering", message)


def _own_packages(repo: Path) -> set[str]:
    packages = set()
    for root in (repo, repo / "src"):
        if root.is_dir():
            for entry in root.iterdir():
                if (entry / "__init__.py").exists() or entry.suffix == ".py":
                    packages.add(entry.stem)
    return packages


def check_internal_mock(change: Change, packages: set[str]) -> Iterator[Finding]:
    """Tests mock only external boundaries, never the project's own modules."""
    if not is_test(change.path):
        return
    for number, text in change.added:
        target = PY_PATCH.search(text)
        own = target is not None and target.group(1).split(".")[0] in packages
        if own or JS_MOCK.search(text):
            message = f"mocks a module of this project: {text.strip()}"
            yield Finding(change.path, number, "internal mock", message)


def _loopback(address: str) -> bool:
    # Loopback and "all interfaces" mean "this machine", not a deployment setting.
    return address.startswith("127.") or address == "0.0.0.0"


def check_hardcoded(change: Change, allow_hosts: tuple[str, ...] = ()) -> Iterator[Finding]:
    """No URLs or IP addresses written into source code, except hosts the project allows."""
    if not is_code(change.path) or is_test(change.path) or CONFIG_PATH.search(change.path):
        return
    safe = SAFE_HOSTS + allow_hosts
    for number, text in change.added:
        hosts = [match.group(1) for match in URL.finditer(text)]
        url = any(not host.endswith(safe) for host in hosts)
        addresses = [match.group(1) for match in IP.finditer(text)]
        if url or any(not _loopback(address) for address in addresses):
            message = f"belongs in config: {text.strip()}"
            yield Finding(change.path, number, "hardcoded config", message)


def check_line_patterns(change: Change) -> Iterator[Finding]:
    """Raw SQL built from strings, and debug leftovers."""
    if not is_code(change.path):
        return
    for number, text in change.added:
        if RAW_SQL.search(text):
            message = f"SQL built from strings; use parameters: {text.strip()}"
            yield Finding(change.path, number, "raw sql", message)
        if DEBUG.search(text):
            yield Finding(change.path, number, "debug leftover", text.strip())


def check_message(message: str) -> list[Finding]:
    """A commit is one line `type(scope): description`, at most 72 characters."""
    text = message.strip("\n")
    problems = []
    if "\n" in text:
        problems.append("one line only: no body, no trailers")
    first = text.split("\n", 1)[0]
    if not COMMIT.fullmatch(first) or not first.split(":", 1)[1].strip():
        problems.append("format is type(scope): description, type one of feat fix refactor docs")
    if len(first) > 72:
        problems.append(f"{len(first)} characters, limit 72")
    return [Finding("message", 1, "commit format", problem) for problem in problems]


def run_checks(
    repo: Path,
    *,
    base: str | None = None,
    network: bool = True,
    allow_test_changes: bool = False,
    limits: Limits | None = None,
    allow_hosts: tuple[str, ...] = (),
    fetch: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[Finding]:
    """Run every check on the staged change, or on HEAD against `base`."""
    limits = limits or Limits()
    own = _own_packages(repo)
    found: list[Finding] = []
    for change in changes(repo, base):
        found += check_size(change, limits)
        found += check_dump_name(change)
        found += check_type_escape(change)
        found += check_internal_mock(change, own)
        found += check_hardcoded(change, allow_hosts)
        found += check_line_patterns(change)
        if not allow_test_changes:
            found += check_test_tampering(change)
    if not allow_test_changes:
        found += [
            Finding(path, 0, "test tampering", "test file deleted")
            for path in deleted_paths(repo, base)
            if is_test(path)
        ]
    if network:
        added = sorted(packages.added_dependencies(changes(repo, base)))
        problems = packages.check(added, fetch or packages.fetch_json)
        found += [Finding(label, 0, "package", message) for label, message in problems]
    return found


def report(
    repo: Path,
    settings: dict[str, Any],
    message: str | None = None,
    *,
    base: str | None = None,
    network: bool = True,
    allow_test_changes: bool = False,
) -> list[str]:
    """Run the checks under a project's `checks` settings; one line per finding."""
    limits = Limits(
        file_lines=int(settings.get("file_lines", Limits.file_lines)),
        function_lines=int(settings.get("function_lines", Limits.function_lines)),
    )
    found = run_checks(
        repo,
        base=base,
        network=network,
        allow_test_changes=allow_test_changes,
        limits=limits,
        allow_hosts=tuple(settings.get("allow_hosts", ())),
    )
    if message is not None and settings.get("commit_format", True):
        found += check_message(message)
    ignore = list(settings.get("ignore", []))
    return [
        f"{f.path}:{f.line}: {f.check}: {f.message}"
        for f in found
        if not any(fnmatch.fnmatch(f.path, glob) for glob in ignore)
    ]
