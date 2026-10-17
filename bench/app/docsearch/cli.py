"""`python -m docsearch.cli index <folder> <index.json>` and `search <index.json> <query>`."""

from __future__ import annotations

import sys
from pathlib import Path

from .chunk import split
from .index import Index
from .load import load
from .search import search


def main(argv: list[str]) -> int:
    """Build an index or search one."""
    if argv[:1] == ["index"] and len(argv) == 3:
        index = Index()
        for document in load(Path(argv[1])):
            for chunk in split(document.name, document.text):
                index.add(chunk)
        index.save(Path(argv[2]))
        print(f"indexed {len(index.chunks)} chunks")
        return 0
    if argv[:1] == ["search"] and len(argv) >= 3:
        for hit in search(Index.load(Path(argv[1])), " ".join(argv[2:])):
            print(f"{hit.score:8.4f}  {hit.document}#{hit.number}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
