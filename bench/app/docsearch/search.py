"""Rank chunks for a query with BM25."""

from __future__ import annotations

from dataclasses import dataclass

from .index import Index

K1 = 1.5
B = 0.75


@dataclass(frozen=True)
class Hit:
    """A chunk that matches, with its score."""

    document: str
    number: int
    score: float


def search(index: Index, query: str, limit: int = 10) -> list[Hit]:
    """The best chunks for the query, best first; an empty query finds nothing."""
    words = [w.lower() for w in query.split()]
    if not words or not index.chunks:
        return []
    average = sum(sum(c["counts"].values()) for c in index.chunks) / len(index.chunks)
    hits = []
    for chunk in index.chunks:
        length = sum(chunk["counts"].values())
        score = 0.0
        for word in words:
            tf = chunk["counts"].get(word, 0)
            if tf:
                norm = tf + K1 * (1 - B + B * length / average)
                score += index.idf(word) * tf * (K1 + 1) / norm
        if score > 0:
            hits.append(Hit(chunk["document"], chunk["number"], round(score, 4)))
    return sorted(hits, key=lambda h: (-h.score, h.document, h.number))[:limit]
