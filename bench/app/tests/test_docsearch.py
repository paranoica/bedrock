from pathlib import Path

from docsearch.chunk import split
from docsearch.index import Index, terms
from docsearch.load import load
from docsearch.search import search


def test_load_reads_text_files(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha beta", encoding="utf-8")
    (tmp_path / "b.txt").write_text("gamma", encoding="utf-8")
    (tmp_path / "c.png").write_bytes(b"\x89PNG")
    assert [d.name for d in load(tmp_path)] == ["a.md", "b.txt"]


def test_split_cuts_words_into_chunks() -> None:
    chunks = split("d", " ".join(f"w{i}" for i in range(10)), size=5)
    assert [len(c.words) for c in chunks] == [5, 5]


def test_short_text_is_one_chunk() -> None:
    assert [c.words for c in split("d", "one two", size=5)] == [("one", "two")]


def test_terms_are_case_folded() -> None:
    assert terms("Hello, World") == ["hello", "world"]


def test_search_ranks_the_matching_chunk_first() -> None:
    index = Index()
    for number, text in enumerate(["the cat sat", "a dog ran", "the cat ran far"]):
        index.add(split(f"doc{number}", text)[0])
    hits = search(index, "dog")
    assert [h.document for h in hits] == ["doc1"]


def test_empty_query_finds_nothing() -> None:
    index = Index()
    index.add(split("d", "words here")[0])
    assert search(index, "   ") == []


def test_index_round_trips_through_json(tmp_path: Path) -> None:
    index = Index()
    index.add(split("d", "alpha beta")[0])
    index.save(tmp_path / "i.json")
    assert Index.load(tmp_path / "i.json").chunks == index.chunks
