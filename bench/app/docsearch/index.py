"""An inverted index over chunks, saved as JSON."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .chunk import Chunk

WORD = re.compile(r"\w+")


def terms(text: str) -> list[str]:
    """The words of a text, case-folded."""
    return [w.casefold() for w in WORD.findall(text)]


class Index:
    """Chunks, their term counts, and how many chunks hold each term."""

    def __init__(self) -> None:
        """An empty index."""
        self.chunks: list[dict] = []
        self.frequency: Counter[str] = Counter()

    def add(self, chunk: Chunk) -> None:
        """Index one chunk."""
        counts = Counter(terms(" ".join(chunk.words)))
        self.chunks.append(
            {"document": chunk.document, "number": chunk.number, "counts": dict(counts)}
        )
        for term, count in counts.items():
            self.frequency[term] += count

    def idf(self, term: str) -> float:
        """Inverse document frequency, BM25 style."""
        n, df = len(self.chunks), self.frequency.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def save(self, path: Path) -> None:
        """Write the index as JSON."""
        path.write_text(json.dumps({"chunks": self.chunks, "frequency": self.frequency}))

    @classmethod
    def load(cls, path: Path) -> Index:
        """Read an index written by `save`."""
        data = json.loads(path.read_text())
        index = cls()
        index.chunks = data["chunks"]
        index.frequency = Counter(data["frequency"])
        return index
