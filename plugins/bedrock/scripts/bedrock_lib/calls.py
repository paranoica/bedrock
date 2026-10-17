"""The call archive (D057): raw transcripts kept as received, quote checks, search.

One folder per call under `<days_dir>/<project>/calls/<id>/`: the raw `transcript.txt`, made
read-only, and `meta.json` with its source, participants, duration, language and checksum.
A debrief in the knowledge base cites the call by id; every item quotes it verbatim with a
timecode, and `check_quotes` proves each quote is in the transcript near that time.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import SAFE_NAME, UserConfig
from .daylog import project_dir

STAMP = re.compile(r"^\[(\d{1,2}:)?(\d{1,2}):(\d{2})\]\s*")
QUOTE = re.compile(r"«([^»]+)»|“([^”]+)”|\"([^\"]+)\"")
CITE = re.compile(r"@\s*((?:\d{1,2}:)?\d{1,2}:\d{2})")
ITEM_SECTIONS = {"decided", "we owe", "they owe", "new facts"}
# A speaker is one to three capitalised words ("Alice", "Speaker 2"), never a sentence.
SPEAKER = re.compile(r"^[^\W\d_a-zа-яё][\w'-]*(?: [^\W_a-zа-яё][\w'-]*){0,2}:\s+")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^#{2,3}\s+(.+?):?\s*$")
NEAR_SECONDS = 60


class CallError(Exception):
    """A call cannot be archived or found."""


@dataclass(frozen=True)
class Problem:
    """A debrief line whose quote is missing, misplaced or absent."""

    line: int
    quote: str
    reason: str


@dataclass(frozen=True)
class Hit:
    """A transcript line that matches a search."""

    call: str
    time: str
    text: str


def _folder(cfg: UserConfig, project: str, call_id: str) -> Path:
    if not SAFE_NAME.match(call_id or ""):
        raise CallError(f"call id '{call_id}' is not a safe folder name")
    return project_dir(cfg, project) / "calls" / call_id


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")[:40] or "call"


def _seconds(stamp: str) -> int:
    parts = [int(p) for p in stamp.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _clock(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _lines(text: str, speakers: bool = False) -> list[tuple[int | None, str]]:
    """Each line with its time: its own stamp, or the last one above it.

    The speaker's name is dropped unless asked for, so a quote can run on across lines.
    """
    found: list[tuple[int | None, str]] = []
    stamp: int | None = None
    for raw in text.splitlines():
        match = STAMP.match(raw)
        if match:
            stamp = _seconds(raw[1 : match.end()].strip().rstrip("]"))
            raw = raw[match.end() :]
            raw = raw if speakers else SPEAKER.sub("", raw, count=1)
        found.append((stamp, raw))
    return found


def normalise(text: str) -> str:
    """Case-folded words separated by single spaces, punctuation dropped."""
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())


def add(
    cfg: UserConfig,
    project: str,
    transcript: Path,
    *,
    source: str,
    title: str,
    day: str,
    participants: list[str],
    language: str,
) -> str:
    """Archive a raw transcript unchanged and return the call id."""
    data = transcript.read_bytes()
    base = f"{day}-{_slug(title)}"
    call_id, number = base, 1
    while (project_dir(cfg, project) / "calls" / call_id).exists():
        number += 1
        call_id = f"{base}-{number}"
    folder = _folder(cfg, project, call_id)
    folder.mkdir(parents=True)
    target = folder / "transcript.txt"
    target.write_bytes(data)
    target.chmod(0o444)
    stamps = [s for s, _ in _lines(data.decode("utf-8", "replace")) if s is not None]
    meta = {
        "id": call_id,
        "title": title,
        "date": day,
        "source": source,
        "participants": participants,
        "language": language,
        "duration": _clock(max(stamps)) if stamps else None,
        "sha256": hashlib.sha256(data).hexdigest(),
        "added": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    return call_id


def _transcript(cfg: UserConfig, project: str, call_id: str) -> tuple[bytes, dict]:
    folder = _folder(cfg, project, call_id)
    try:
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        return (folder / "transcript.txt").read_bytes(), meta
    except (OSError, json.JSONDecodeError) as error:
        raise CallError(f"call {call_id} is not in the archive: {error}") from error


def verify(cfg: UserConfig, project: str, call_id: str) -> bool:
    """True when the raw transcript still matches the checksum taken when it was archived."""
    data, meta = _transcript(cfg, project, call_id)
    return hashlib.sha256(data).hexdigest() == meta.get("sha256")


def _locate(lines: list[tuple[int | None, str]], quote: str) -> list[int | None]:
    """Stamps of the lines where the quote starts; a quote may run on into the next lines."""
    words = [normalise(text) for _, text in lines]
    starts = []
    for index in range(len(lines)):
        joined = " " + " ".join(w for w in words[index : index + 3] if w) + " "
        at = joined.find(f" {quote} ")
        if words[index] and at != -1 and at < len(words[index]) + 1:
            starts.append(lines[index][0])
    return starts


def _check_line(lines: list[tuple[int | None, str]], number: int, line: str) -> list[Problem]:
    quotes = [next(g for g in m.groups() if g) for m in QUOTE.finditer(line)]
    cited = CITE.search(line)
    if not quotes or not cited:
        return [Problem(number, "", "an item needs a verbatim quote and (call-id @ hh:mm:ss)")]
    problems = []
    for quote in quotes:
        if not normalise(quote):
            problems.append(Problem(number, quote, "the quote has no words"))
            continue
        stamps = _locate(lines, normalise(quote))
        if not stamps:
            problems.append(Problem(number, quote, "not in the transcript"))
            continue
        want = _seconds(cited.group(1))
        known = [s for s in stamps if s is not None]
        if known and not any(abs(s - want) <= NEAR_SECONDS for s in known):
            found = ", ".join(_clock(s) for s in known)
            problems.append(Problem(number, quote, f"found at {found}, cited {_clock(want)}"))
    return problems


def check_quotes(cfg: UserConfig, project: str, call_id: str, debrief: str) -> list[Problem]:
    """Check every item of a debrief's item sections against the call's transcript."""
    data, _ = _transcript(cfg, project, call_id)
    lines = _lines(data.decode("utf-8", "replace"))
    problems: list[Problem] = []
    section = ""
    for number, line in enumerate(debrief.splitlines(), start=1):
        if heading := HEADING.match(line):
            section = heading.group(1).strip().casefold()
        elif section in ITEM_SECTIONS and ITEM.match(line):
            problems += _check_line(lines, number, line)
    return problems


def search(cfg: UserConfig, project: str, text: str) -> list[Hit]:
    """Every transcript line of a project's calls that contains the text, oldest call first."""
    wanted = normalise(text)
    folder = project_dir(cfg, project) / "calls"
    hits = []
    for call in sorted(folder.iterdir()) if folder.is_dir() else []:
        data = (call / "transcript.txt").read_bytes() if (call / "transcript.txt").exists() else b""
        for stamp, line in _lines(data.decode("utf-8", "replace"), speakers=True):
            if wanted and wanted in normalise(line):
                hits.append(Hit(call.name, _clock(stamp) if stamp is not None else "", line))
    return hits
