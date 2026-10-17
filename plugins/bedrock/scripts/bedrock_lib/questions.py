"""The per-project question log: every owner question, its answer, and lookup of earlier ones."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import clock, jsonl
from .config import SAFE_NAME, UserConfig

WORD = re.compile(r"\w+", re.UNICODE)
STEM = 5
MIN_SCORE = 0.3
STOPWORDS = {
    "а", "в", "во", "и", "к", "как", "на", "но", "о", "по", "с", "у", "что", "это", "мы", "нас",
    "ли", "же", "ну", "вот", "слушай", "скажи", "где", "когда", "почему", "зачем", "из",
    "a", "an", "the", "how", "do", "does", "did", "we", "our", "is", "are", "to", "into", "of",
    "in", "on", "for", "what", "where", "why", "when", "and", "or", "it", "this", "that",
}  # fmt: skip


class QuestionError(Exception):
    """A question-log operation cannot be done as asked."""


@dataclass(frozen=True)
class Match:
    """An earlier question found similar to a new one."""

    score: float
    record: dict[str, Any]


def path(cfg: UserConfig, project: str) -> Path:
    """Return the project's question log; the project name must be a safe folder name."""
    if not SAFE_NAME.match(project):
        raise QuestionError(f"project name '{project}' is not a safe folder name")
    return cfg.days_dir / project / "questions.jsonl"


def terms(text: str) -> set[str]:
    """Reduce a question to its content words, crudely stemmed so word forms still meet."""
    words = (word.lower() for word in WORD.findall(text))
    return {word[:STEM] for word in words if word not in STOPWORDS and len(word) > 1}


def log_question(
    cfg: UserConfig, project: str, question: str, session: str = "", now: datetime | None = None
) -> str:
    """Append a question and return its id."""
    stamp = clock.iso(now or clock.now_utc())
    qid = secrets.token_hex(6)
    record = {"type": "question", "id": qid, "ts": stamp, "session": session, "question": question}
    jsonl.append(path(cfg, project), record)
    return qid


def answer(cfg: UserConfig, project: str, qid: str, text: str, source: str) -> None:
    """Append the answer to an earlier question."""
    known = {r["id"] for r in jsonl.read(path(cfg, project)) if r.get("type") == "question"}
    if qid not in known:
        raise QuestionError(f"no question with id '{qid}'")
    record = {"type": "answer", "id": qid, "answer": text, "source": source}
    jsonl.append(path(cfg, project), record)


def history(cfg: UserConfig, project: str) -> list[dict[str, Any]]:
    """Return every question with its latest answer merged in, oldest first."""
    merged: dict[str, dict[str, Any]] = {}
    for record in jsonl.read(path(cfg, project)):
        if record.get("type") == "question":
            merged[record["id"]] = dict(record)
        elif record.get("type") == "answer" and record["id"] in merged:
            merged[record["id"]].update(answer=record["answer"], source=record["source"])
    return list(merged.values())


def similar(cfg: UserConfig, project: str, question: str, limit: int = 5) -> list[Match]:
    """Return earlier questions whose content words overlap the new one, best first."""
    wanted = terms(question)
    if not wanted:
        return []
    matches: list[Match] = []
    for record in history(cfg, project):
        known = terms(record["question"])
        score = len(wanted & known) / len(wanted | known) if known else 0.0
        if score >= MIN_SCORE:
            matches.append(Match(score, record))
    return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]
