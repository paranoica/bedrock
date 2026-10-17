"""The knowledge base: one folder per project in a local git store (D023 to D027).

Notes, their frontmatter and links; the validator; the drift detector against the code;
modules without a note; backlinks; and creating a project's minimal folder.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

TEMPLATES = Path(__file__).resolve().parents[2] / "templates" / "kb"
LINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
FIELDS = ("type", "tags", "parent", "updated")
TYPE_FIELDS = {
    "decision": ("code", "status", "date", "decided_by"),
    "failure": ("code",),
    "module": ("covers", "verified_at"),
    "runbook": ("verified",),
    "faq": ("verified_at",),
    "call": ("date",),
}
HEADINGS = {
    "decision": ("Decision", "Why", "Rejected", "Consequences", "Does not cancel", "Risk accepted"),
    "failure": ("Tried", "Failed because", "Mechanism", "Caught now by"),
    "module": ("Purpose", "Boundaries", "Rules", "Pitfalls"),
    "handoff": (
        "Role", "Context", "Decided, do not reopen", "Hard constraints", "Read, in order",
        "Task", "Done when", "Do not", "Traps", "Where the result goes",
    ),
    "call": ("Decided", "We owe", "They owe", "New facts"),
    "runbook": ("Steps", "Check it worked", "Traps"),
    "faq": ("Answer", "Source"),
    "status": ("Now", "Blocked", "Next"),
}  # fmt: skip
NOT_ORPHANS = {"entry", "summary"}
EDIT_HISTORY = re.compile(
    r"\bpreviously\b|\bupdated on\b|\bwas changed\b|\bused to be\b|~~[^~]+~~"
    r"|^\s*(?:upd|edit|update)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
MAX_LINES = 300
RUNBOOK_DAYS = 30
INDEXES = ("architecture", "decisions", "failures", "runbooks", "handoffs", "open-questions")


@dataclass
class Note:
    """One note: its name (file stem), frontmatter, body and the names it links to."""

    name: str
    meta: dict[str, Any]
    body: str
    path: Path | None = None
    links: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Problem:
    """One validator finding, with the fix in the message."""

    path: str
    message: str


def _value(text: str) -> Any:
    text = text.strip()
    if text.startswith("[") and text.endswith("]") and not text.startswith("[["):
        return [item.strip().strip("'\"") for item in text[1:-1].split(",") if item.strip()]
    return text.strip("'\"")


def parse(name: str, text: str, path: Path | None = None) -> Note:
    """Split a note into frontmatter (a flat YAML subset) and body, and collect its links."""
    meta: dict[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        head, sep, rest = text[4:].partition("\n---")
        if sep:
            body = rest.split("\n", 1)[1] if "\n" in rest else ""
            for line in head.splitlines():
                key, colon, value = line.partition(":")
                if colon and key.strip() and not key.startswith(" "):
                    meta[key.strip()] = _value(value)
    links = [match.group(1).strip().split("/")[-1] for match in LINK.finditer(text)]
    return Note(name, meta, body, path, links)


def notes(bank: Path, project: str) -> dict[str, Note]:
    """Every note of a project and of `_shared`, by name."""
    found: dict[str, Note] = {}
    for folder in (bank / "_shared", bank / project):
        for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
            found[path.stem] = parse(path.stem, path.read_text(encoding="utf-8"), path)
    return found


def _rel(bank: Path, note: Note) -> str:
    return str(note.path.relative_to(bank)) if note.path else note.name


def _shape(note: Note) -> list[str]:
    kind = str(note.meta.get("type", ""))
    missing = [f for f in (*FIELDS, *TYPE_FIELDS.get(kind, ())) if f not in note.meta]
    found = [f"missing field '{f}'" for f in missing]
    headings = set(re.findall(r"^##\s+(.+?)\s*$", note.body, re.MULTILINE))
    found += [f"missing heading '{h}'" for h in HEADINGS.get(kind, ()) if h not in headings]
    return found


def _content(note: Note, code: str, today: date) -> list[str]:
    found = []
    kind = note.meta.get("type")
    if kind in ("decision", "failure") and code:
        prefix = f"{code}-{'D' if kind == 'decision' else 'F'}"
        if not str(note.meta.get("code", "")).startswith(prefix):
            found.append(f"code '{note.meta.get('code')}' lacks the project prefix {prefix}")
    if EDIT_HISTORY.search(note.body):
        found.append("edit history in the body: state the current fact, git keeps the history")
    if note.body.count("\n") > MAX_LINES:
        found.append(f"over {MAX_LINES} lines: split it into notes of one topic each")
    if kind == "runbook" and _days(note.meta.get("verified"), today) > RUNBOOK_DAYS:
        found.append(f"verified over {RUNBOOK_DAYS} days ago: re-verify the steps, then the date")
    return found


def _days(stamp: Any, today: date) -> int:
    try:
        return (today - date.fromisoformat(str(stamp))).days
    except ValueError:
        return 0


def validate(bank: Path, project: str, today: str | None = None) -> list[Problem]:
    """Return every problem in a project's notes (D025, D026.2)."""
    day = date.fromisoformat(today) if today else date.today()
    found = notes(bank, project)
    entry = found.get("entry")
    code = str(entry.meta.get("code", "")) if entry else ""
    superseded = {n.name for n in found.values() if n.meta.get("status") == "superseded"}
    inbound = {name for note in found.values() for name in note.links if name != note.name}
    problems = []
    for note in found.values():
        if note.path is None or not note.path.is_relative_to(bank / project):
            continue
        messages = _shape(note) + _content(note, code, day)
        messages += [f"broken link [[{link}]]" for link in note.links if link not in found]
        for line in note.body.splitlines():
            for link in LINK.findall(line):
                if link in superseded and "supersed" not in line.lower():
                    messages.append(f"links superseded {link} as current: point to its successor")
        if note.name not in inbound and note.name not in NOT_ORPHANS:
            messages.append("orphan: no note links here; link it from its index or delete it")
        problems += [Problem(_rel(bank, note), message) for message in messages]
    return problems


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, timeout=30
    )


def covers(note: Note) -> list[str]:
    """The paths a module note covers."""
    value = note.meta.get("covers") or []
    return [str(item).rstrip("/") for item in (value if isinstance(value, list) else [value])]


def drift(bank: Path, project: str, repo: Path) -> list[str]:
    """List module notes whose covered code changed since the commit they were verified at."""
    found = []
    for note in notes(bank, project).values():
        if note.meta.get("type") != "module" or not covers(note):
            continue
        commit = str(note.meta.get("verified_at", ""))
        if _git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            found.append(f"note {note.name}: verified_at {commit!r} is an unknown commit")
            continue
        changed = _git(repo, "diff", "--name-only", commit, "HEAD", "--", *covers(note))
        files = changed.stdout.split()
        anchors = note.meta.get("anchors") or []
        if files and anchors:
            patch = _git(repo, "diff", "-U0", commit, "HEAD", "--", *covers(note)).stdout
            changed_lines = [
                row
                for row in patch.splitlines()
                if row.startswith(("@@", "+", "-")) and not row.startswith(("+++", "---"))
            ]
            touched = any(anchor in row for row in changed_lines for anchor in anchors)
            files = files if touched else []
        if files:
            found.append(
                f"note {note.name} is stale: {', '.join(files)} changed since {commit[:10]}; "
                "update § Boundaries/Rules or record that nothing changes and why (D026)"
            )
    return found


def covering(bank: Path, project: str, paths: list[str]) -> list[Note]:
    """Module notes whose covered paths include any of the given files."""

    def under(path: str, cover: str) -> bool:
        return path == cover or path.startswith(cover + "/")

    return [
        note
        for note in notes(bank, project).values()
        if note.meta.get("type") == "module"
        and any(under(p, c) for p in paths for c in covers(note))
    ]


def uncovered(bank: Path, project: str, repo: Path, roots: list[str]) -> list[str]:
    """Top-level modules under the given roots that no module note covers (D026.6)."""
    covered = [c for n in notes(bank, project).values() for c in covers(n)]
    missing = []
    for root in roots:
        children = (p for p in (repo / root).iterdir() if p.is_dir() and not p.name.startswith("."))
        for child in sorted(children):
            rel = child.relative_to(repo).as_posix()
            if not any(
                rel == c or rel.startswith(c + "/") or c.startswith(rel + "/") for c in covered
            ):
                missing.append(rel)
    return missing


def backlinks(bank: Path, project: str, name: str) -> list[str]:
    """Names of the notes that link to `name`."""
    return sorted(
        n.name for n in notes(bank, project).values() if name in n.links and n.name != name
    )


def _render(template: str, values: dict[str, str]) -> str:
    text = (TEMPLATES / f"{template}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def init(bank: Path, project: str, code: str, today: str | None = None) -> Path:
    """Create a project's minimal folder (D024) and the store's git repository if missing."""
    day = today or date.today().isoformat()
    folder = bank / project
    folder.mkdir(parents=True, exist_ok=True)
    values = {"project": project, "code": code, "date": day}
    for name in ("entry", "summary", "status"):
        target = folder / f"{name}.md"
        if not target.exists():
            target.write_text(_render(name, values), encoding="utf-8")
    for name in INDEXES:
        target = folder / f"{name}.md"
        if not target.exists():
            title = name.replace("-", " ").capitalize()
            head = f'---\ntype: index\ntags: [index]\nparent: "[[entry]]"\nupdated: {day}\n---\n'
            target.write_text(f"{head}# {title}\n", encoding="utf-8")
    if not (bank / ".git").exists():
        _git(bank, "init", "-q")
    return folder
