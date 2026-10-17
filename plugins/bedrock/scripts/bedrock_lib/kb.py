"""The knowledge base: one folder per project in a local git store (D023 to D027).

Notes, their frontmatter and links; the validator; modules without a note; backlinks; and
creating a project's minimal folder. Drift against the code lives in `kbdrift`.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from .codemap import SKIP_DIRS

TEMPLATES = Path(__file__).resolve().parents[2] / "templates" / "kb"
LINK = re.compile(r"\[\[([^\]|#]+?)\\?(?:[#|][^\]]*)?\]\]")
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
PLACEHOLDER = re.compile(r"^\{.*\}$|^\[\{.*\}\]$")
FIELDS = ("type", "tags", "parent", "updated")
DATE_FIELDS = ("updated", "date", "verified")
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
HISTORY_TYPES = {"failure", "call"}
EDIT_HISTORY = re.compile(
    r"\bpreviously\b|\bupdated on\b|\bwas changed\b|\bused to be\b|~~[^~]+~~"
    r"|^\s*(?:upd|edit|update)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
MAX_LINES = 300
RUNBOOK_DAYS = 30
INDEXES = (
    "architecture",
    "decisions",
    "failures",
    "runbooks",
    "handoffs",
    "faq",
    "open-questions",
)


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


def _frontmatter(head: str) -> dict[str, Any]:
    """A flat YAML subset: `key: value`, `key: [a, b]` and block lists of `- item`."""
    meta: dict[str, Any] = {}
    current: str | None = None
    for line in head.splitlines():
        stripped = line.strip()
        if current and stripped.startswith("- "):
            items = meta[current] if isinstance(meta[current], list) else []
            meta[current] = [*items, stripped[2:].strip().strip("'\"")]
            continue
        key, colon, value = line.partition(":")
        if colon and key.strip() and not key.startswith(" "):
            current = key.strip()
            meta[current] = _value(value) if value.strip() else []
            if value.strip():
                current = None
    return {key: ("" if value == [] else value) for key, value in meta.items()}


def _links(text: str) -> list[str]:
    visible = FENCE.sub("", text)
    return [match.group(1).strip().rstrip("\\").split("/")[-1] for match in LINK.finditer(visible)]


def parse(name: str, text: str, path: Path | None = None) -> Note:
    """Split a note into frontmatter and body, and collect its links (code fences ignored)."""
    meta: dict[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        head, sep, rest = text[4:].partition("\n---")
        if sep:
            body = rest.split("\n", 1)[1] if "\n" in rest else ""
            meta = _frontmatter(head)
    return Note(name, meta, body, path, _links(text))


def all_notes(bank: Path, project: str) -> list[Note]:
    """Every note of a project and of `_shared`, one entry per file."""
    found = []
    for folder in (bank / "_shared", bank / project):
        for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
            found.append(parse(path.stem, path.read_text(encoding="utf-8"), path))
    return found


def notes(bank: Path, project: str) -> dict[str, Note]:
    """Notes by name; a project note shadows a `_shared` one (the validator flags it)."""
    return {note.name: note for note in all_notes(bank, project)}


def _rel(bank: Path, note: Note) -> str:
    return str(note.path.relative_to(bank)) if note.path else note.name


def empty(value: Any) -> bool:
    """True for a missing value: blank, an empty list, or a `{placeholder}` left from a template."""
    if isinstance(value, list):
        return not value or all(PLACEHOLDER.match(str(item)) for item in value)
    return not str(value).strip() or bool(PLACEHOLDER.match(str(value).strip()))


def _parse_date(text: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _shape(note: Note) -> list[str]:
    kind = str(note.meta.get("type", ""))
    base = [f for f in FIELDS if not (kind == "entry" and f == "parent")]
    wanted = (*base, *TYPE_FIELDS.get(kind, ()))
    found = [f"missing field '{f}'" for f in wanted if empty(note.meta.get(f, ""))]
    for key in DATE_FIELDS:
        value = str(note.meta.get(key, "")).strip()
        if value and not empty(value) and _parse_date(value) is None:
            found.append(f"field '{key}' is not a date (YYYY-MM-DD): {value!r}")
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
    if kind not in HISTORY_TYPES and EDIT_HISTORY.search(FENCE.sub("", note.body)):
        found.append("edit history in the body: state the current fact, git keeps the history")
    if note.body.count("\n") > MAX_LINES:
        found.append(f"over {MAX_LINES} lines: split it into notes of one topic each")
    verified = _parse_date(str(note.meta.get("verified", "")))
    if kind == "runbook" and verified and (today - verified).days > RUNBOOK_DAYS:
        found.append(f"verified over {RUNBOOK_DAYS} days ago: re-verify the steps, then the date")
    return found


def _handoff(note: Note, decisions: list[Note]) -> list[str]:
    if note.meta.get("type") != "handoff" or note.meta.get("status") == "done":
        return []
    written = _parse_date(str(note.meta.get("updated", "")))
    newer = [
        d.name
        for d in decisions
        if written and (when := _parse_date(str(d.meta.get("date", "")))) and when > written
    ]
    if newer:
        return [
            f"re-check before use: decisions newer than this handoff: {', '.join(newer)}; "
            "read them, then set `updated` to today, or `status: done` once its task is finished"
        ]
    return []


def _collisions(found: list[Note], bank: Path) -> list[Problem]:
    seen: dict[str, Note] = {}
    problems = []
    for note in found:
        if note.name in seen:
            other = _rel(bank, seen[note.name])
            problems.append(Problem(_rel(bank, note), f"name collision with {other}: rename one"))
        else:
            seen[note.name] = note
    return problems


def validate(bank: Path, project: str, today: str | None = None) -> list[Problem]:
    """Return every problem in a project's notes (D025, D026.2)."""
    day = date.fromisoformat(today) if today else date.today()
    found = all_notes(bank, project)
    names = {note.name for note in found}
    entry = next((n for n in found if n.name == "entry"), None)
    code = str(entry.meta.get("code", "")) if entry else ""
    decisions = [n for n in found if n.meta.get("type") == "decision"]
    superseded = {n.name for n in decisions if n.meta.get("status") == "superseded"}
    inbound = {name for note in found for name in note.links if name != note.name}
    problems = _collisions(found, bank)
    for note in found:
        if note.path is None or not note.path.is_relative_to(bank / project):
            continue
        messages = _shape(note) + _content(note, code, day) + _handoff(note, decisions)
        messages += [f"broken link [[{link}]]" for link in note.links if link not in names]
        for line in FENCE.sub("", note.body).splitlines():
            for link in _links(line):
                if link in superseded and "supersed" not in line.lower():
                    messages.append(f"links superseded {link} as current: point to its successor")
        if note.name not in inbound and note.name not in NOT_ORPHANS:
            messages.append("orphan: no note links here; link it from its index or delete it")
        problems += [Problem(_rel(bank, note), message) for message in messages]
    return problems


def fingerprint(text: str) -> str:
    """A hash of a note that ignores restamping `verified_at` and `updated` in its frontmatter."""
    head, body = "", text
    if text.startswith("---\n") and "\n---" in text[4:]:
        split = text.index("\n---", 4)
        head, body = text[:split], text[split:]
    kept = [line for line in head.splitlines() if not re.match(r"(verified_at|updated)\s*:", line)]
    return hashlib.sha256("\n".join([*kept, body]).encode("utf-8")).hexdigest()


def covers(note: Note) -> list[str]:
    """The paths a module note covers (placeholders left from the template are not paths)."""
    value = note.meta.get("covers") or []
    items = value if isinstance(value, list) else [value]
    return [str(item).rstrip("/") for item in items if str(item).strip() and not empty(item)]


def under(path: str, cover: str) -> bool:
    """True when a repository path is the covered path or inside it."""
    return path == cover or path.startswith(cover + "/")


def covering(bank: Path, project: str, paths: list[str]) -> list[Note]:
    """Module notes whose covered paths include any of the given files."""
    return [
        note
        for note in all_notes(bank, project)
        if note.meta.get("type") == "module"
        and any(under(p, c) for p in paths for c in covers(note))
    ]


def uncovered(bank: Path, project: str, repo: Path, roots: list[str]) -> list[str]:
    """Top-level modules under the given roots that no module note covers (D026.6)."""
    covered = [c for n in all_notes(bank, project) for c in covers(n)]
    missing = []
    top = repo.resolve()
    for root in roots:
        folder = (repo / root).resolve()
        if not folder.is_dir() or not folder.is_relative_to(top):
            continue
        children = (
            p
            for p in folder.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP_DIRS
        )
        for child in sorted(children):
            rel = child.relative_to(top).as_posix()
            if not any(under(rel, c) or c.startswith(rel + "/") for c in covered):
                missing.append(rel)
    return missing


def backlinks(bank: Path, project: str, name: str) -> list[str]:
    """Names of the notes that link to `name`."""
    return sorted(n.name for n in all_notes(bank, project) if name in n.links and n.name != name)


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
        subprocess.run(["git", "-C", str(bank), "init", "-q"], capture_output=True, check=False)
    return folder
