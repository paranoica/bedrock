"""Append-only JSON Lines files, safe for several writers on one machine."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any


class JsonlError(Exception):
    """A JSON Lines file holds a line that is not valid JSON."""


def dumps(value: Any, separators: tuple[str, str] | None = None) -> str:
    """One line of JSON that can always be written as UTF-8.

    Text read with `surrogateescape` (file names that are not UTF-8) cannot be encoded as is;
    such a value falls back to ASCII escapes, which JSON readers accept.
    """
    text = json.dumps(value, ensure_ascii=False, separators=separators)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(value, separators=separators)
    return text


def append(path: Path, record: dict[str, Any]) -> None:
    """Append one record as a line, holding an exclusive lock while writing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = dumps(record, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            handle.write(line)
            handle.flush()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read(path: Path) -> list[dict[str, Any]]:
    """Read every record; a missing file is empty, a corrupt line is an error naming it."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise JsonlError(f"{path}:{number}: {error.msg}") from error
    return records
