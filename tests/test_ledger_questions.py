import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_lib import ledger, questions
from bedrock_lib.config import UserConfig


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


# ledger


def entry(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "project": "Acme",
        "role": "inventory",
        "model": "haiku",
        "reason": "a",
        "estimate": 300000.0,
        "actual": 280000.0,
        "turns": 18,
        "cap_hit": False,
        "accepted": True,
    }
    return base | overrides


def test_ledger_add_stamps_time_and_persists(cfg: UserConfig) -> None:
    ledger.add(cfg, entry(), now=utc("2026-10-17T12:00:00"))
    records = ledger.records(cfg)
    assert records[0]["ts"] == "2026-10-17T12:00:00Z"
    assert records[0]["role"] == "inventory"


def test_ledger_rejects_missing_fields(cfg: UserConfig) -> None:
    bad = entry()
    del bad["role"]
    with pytest.raises(ledger.LedgerError):
        ledger.add(cfg, bad)


def test_ledger_rejects_unknown_reason(cfg: UserConfig) -> None:
    with pytest.raises(ledger.LedgerError):
        ledger.add(cfg, entry(reason="because"))


def test_ledger_summary_groups_by_role(cfg: UserConfig) -> None:
    ledger.add(cfg, entry(), now=utc("2026-10-17T12:00:00"))
    ledger.add(
        cfg, entry(actual=120000.0, cap_hit=True, accepted=False), now=utc("2026-10-17T13:00:00")
    )
    ledger.add(cfg, entry(role="critic", model="opus", reason="b"), now=utc("2026-10-17T14:00:00"))
    summary = ledger.summary(cfg)
    inventory = summary["inventory"]
    assert inventory["count"] == 2
    assert inventory["actual"] == 400000.0
    assert inventory["cap_hits"] == 1
    assert inventory["accepted"] == 1
    assert summary["critic"]["count"] == 1


def test_ledger_summary_since_filters_old_entries(cfg: UserConfig) -> None:
    ledger.add(cfg, entry(), now=utc("2026-10-10T12:00:00"))
    ledger.add(cfg, entry(), now=utc("2026-10-17T12:00:00"))
    assert ledger.summary(cfg, since=utc("2026-10-15T00:00:00"))["inventory"]["count"] == 1


def write_transcript(path: Path, usages: list[tuple[str, dict[str, int]]]) -> Path:
    lines = []
    for message_id, usage in usages:
        lines.append(
            json.dumps({"type": "assistant", "message": {"id": message_id, "usage": usage}})
        )
    lines.append(json.dumps({"type": "user", "message": {"content": "x"}}))
    path.write_text("\n".join(lines) + "\n")
    return path


def test_transcript_spend_weights_and_dedupes(tmp_path: Path) -> None:
    first = {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 2}
    second = {
        "input_tokens": 0,
        "cache_read_input_tokens": 2000,
        "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 0},
        "cache_creation_input_tokens": 100,
        "output_tokens": 50,
    }
    path = write_transcript(tmp_path / "t.jsonl", [("m1", first), ("m1", first), ("m2", second)])
    spend = ledger.transcript_spend(path)
    # m1: 10 + 1000*0.1 + 2*5 = 120 ; m2: 2000*0.1 + 100*1.25 + 50*5 = 575
    assert spend.turns == 2
    assert spend.weighted == pytest.approx(695.0)
    assert spend.start_context == 1010
    assert spend.peak_context == 2100


def test_transcript_spend_of_empty_file_is_zero(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text("")
    spend = ledger.transcript_spend(path)
    assert spend.turns == 0
    assert spend.weighted == 0.0


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


def test_ledger_requires_the_accepted_flag(cfg: UserConfig) -> None:
    bad = entry()
    del bad["accepted"]
    with pytest.raises(ledger.LedgerError):
        ledger.add(cfg, bad)


def test_corrupt_transcript_line_is_a_ledger_error(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text('{"type": "assistant"\n')
    with pytest.raises(ledger.LedgerError, match=r"t\.jsonl:1"):
        ledger.transcript_spend(path)


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


@pytest.mark.parametrize(
    "bad",
    [
        {"estimate": "lots"},
        {"actual": None},
        {"turns": 2.5},
        {"turns": True},
        {"cap_hit": "no"},
        {"accepted": 1},
        {"estimate": -1.0},
        {"estimate": float("nan")},
        {"actual": float("inf")},
    ],
)
def test_ledger_rejects_wrong_field_types(cfg: UserConfig, bad: dict[str, object]) -> None:
    with pytest.raises(ledger.LedgerError):
        ledger.add(cfg, entry(**bad))
    assert ledger.records(cfg) == []


def test_ledger_accepts_integer_spend(cfg: UserConfig) -> None:
    ledger.add(cfg, entry(estimate=0, actual=280000))
    assert ledger.summary(cfg)["inventory"]["estimate"] == 0.0


def test_transcript_spend_skips_synthetic_messages(tmp_path: Path) -> None:
    zero = {"input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}
    real = {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 2}
    lines = [
        {"type": "assistant", "message": {"id": "s1", "model": "<synthetic>", "usage": zero}},
        {"type": "assistant", "message": {"id": "m1", "model": "claude-opus-5-5", "usage": real}},
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    spend = ledger.transcript_spend(path)
    assert spend.turns == 1
    assert spend.start_context == 1010


def test_ledger_accepts_an_unknown_verdict_until_review(cfg: UserConfig) -> None:
    ledger.add(cfg, entry(accepted=None), now=utc("2026-10-17T12:00:00"))
    assert ledger.summary(cfg)["inventory"]["accepted"] == 0
