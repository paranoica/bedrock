"""Read the documents of a folder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True)
class Document:
    """One document: its path relative to the folder, and its text."""

    name: str
    text: str


def load(folder: Path) -> list[Document]:
    """Every text document under the folder, sorted by name."""
    documents = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix in EXTENSIONS:
            documents.append(Document(path.relative_to(folder).as_posix(), path.read_text("utf-8")))
    return documents
