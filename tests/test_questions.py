from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_lib import questions
from bedrock_lib.config import UserConfig


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


# questions


def test_question_log_and_answer(cfg: UserConfig) -> None:
    qid = questions.log_question(
        cfg, "Acme", "Как режутся документы на куски?", now=utc("2026-10-17T12:00:00")
    )
    questions.answer(cfg, "Acme", qid, "По 512 токенов с перекрытием 64.", "ingestion.md")
    found = questions.history(cfg, "Acme")
    assert found[0]["question"] == "Как режутся документы на куски?"
    assert found[0]["answer"] == "По 512 токенов с перекрытием 64."
    assert found[0]["source"] == "ingestion.md"


def test_answer_to_unknown_question_is_an_error(cfg: UserConfig) -> None:
    with pytest.raises(questions.QuestionError):
        questions.answer(cfg, "Acme", "nope", "x", "y")


def test_similar_finds_a_reworded_question(cfg: UserConfig) -> None:
    questions.log_question(cfg, "Acme", "Как режутся документы на куски?")
    questions.log_question(cfg, "Acme", "Где лежат ключи AWS для dev?")
    hits = questions.similar(cfg, "Acme", "слушай, а как документы режутся на куски")
    assert hits
    assert hits[0].record["question"] == "Как режутся документы на куски?"


def test_similar_ignores_unrelated_questions(cfg: UserConfig) -> None:
    questions.log_question(cfg, "Acme", "Где лежат ключи AWS для dev?")
    assert questions.similar(cfg, "Acme", "как документы режутся на куски") == []


def test_similar_on_empty_log_is_empty(cfg: UserConfig) -> None:
    assert questions.similar(cfg, "Acme", "anything") == []


def test_similar_works_in_english(cfg: UserConfig) -> None:
    questions.log_question(cfg, "Acme", "How are documents split into chunks?")
    hits = questions.similar(cfg, "Acme", "how do we split documents into chunks")
    assert hits and hits[0].score > 0.5


def test_same_question_twice_in_one_second_gets_two_ids(cfg: UserConfig) -> None:
    at = utc("2026-10-17T12:00:00")
    first = questions.log_question(cfg, "Acme", "Где ключи?", now=at)
    second = questions.log_question(cfg, "Acme", "Где ключи?", now=at)
    assert first != second
    assert len(questions.history(cfg, "Acme")) == 2


@pytest.mark.parametrize("project", ["../escape", "a/b", "", "Acme\n"])
def test_question_log_rejects_unsafe_project(cfg: UserConfig, project: str) -> None:
    with pytest.raises(questions.QuestionError):
        questions.log_question(cfg, project, "x")
