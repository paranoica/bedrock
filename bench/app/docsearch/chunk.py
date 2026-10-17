"""Cut a document into overlapping chunks of words."""

from __future__ import annotations

from dataclasses import dataclass

SIZE = 200
OVERLAP = 0


@dataclass(frozen=True)
class Chunk:
    """A run of words from one document, with its position."""

    document: str
    number: int
    words: tuple[str, ...]


def split(document: str, text: str, size: int = SIZE, overlap: int = OVERLAP) -> list[Chunk]:
    """Chunks of `size` words; each starts `size - overlap` words after the previous one."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("size must be positive and overlap smaller than size")
    words = text.split()
    step = size - overlap
    chunks = []
    for number, start in enumerate(range(0, len(words) - size + 1, step)):
        chunks.append(Chunk(document, number, tuple(words[start : start + size])))
    if not chunks and words:
        chunks.append(Chunk(document, 0, tuple(words)))
    return chunks
