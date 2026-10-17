import io
import json
from pathlib import Path

import pytest
from bedrock_hooks import dispatch, grants
from bedrock_hooks.registry import RULES
from bedrock_lib import clock, questions, session
from bedrock_lib.config import load_user_config
from conftest import owner_transcript

NOW = "2026-10-17T12:00:00Z"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture
def work(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "bedrock.json").write_text(json.dumps({"project": "Acme"}))
    return root


def environ(home: Path) -> dict[str, str]:
    return {"HOME": str(home), "BEDROCK_NOW": NOW, "PATH": "/usr/bin:/bin"}


def prompt(home: Path, work: Path, text: str, source: str | None = "user") -> dict:
    transcript = owner_transcript(home, text) if source == "user" else ""
    data = {"session_id": "s1", "cwd": str(work), "prompt": text, "transcript_path": transcript}
    if source:
        data["source"] = source
    out = io.StringIO()
    dispatch.main(["UserPromptSubmit"], io.StringIO(json.dumps(data)), out, environ(home), RULES)
    return json.loads(out.getvalue() or "{}")


def cfg(home: Path):
    return load_user_config(environ(home))


def test_grant_is_recorded_and_shown_to_the_owner(home: Path, work: Path) -> None:
    result = prompt(home, work, "запушь")
    assert "push (once, until 17:00)" in result["systemMessage"]
    now = clock.parse(NOW)
    assert grants.available(cfg(home), "push", "Acme", None, now) is not None


@pytest.mark.parametrize("source", ["loop_wakeup", "sdk", "schedule_wakeup"])
def test_only_the_owners_own_prompt_grants(home: Path, work: Path, source: str) -> None:
    prompt(home, work, "запушь", source=source)
    now = clock.parse(NOW)
    assert grants.available(cfg(home), "push", "Acme", None, now) is None


def test_revoke(home: Path, work: Path) -> None:
    prompt(home, work, "до конца плана: пушь")
    result = prompt(home, work, "/bedrock:revoke")
    assert "revoked" in result["systemMessage"]
    now = clock.parse(NOW)
    assert grants.available(cfg(home), "push", "Acme", None, now) is None


@pytest.mark.parametrize(
    ("text", "mode"),
    [("сегодня до талого", "max"), ("экономим", "save"), ("обычный режим", "normal")],
)
def test_spend_mode_switch(home: Path, work: Path, text: str, mode: str) -> None:
    result = prompt(home, work, text)
    stored = json.loads((home / ".local/state/bedrock/spend.json").read_text())
    assert stored["mode"] == mode
    assert mode in result["systemMessage"]


def test_question_is_logged(home: Path, work: Path) -> None:
    prompt(home, work, "Как режутся документы на куски?")
    assert questions.history(cfg(home), "Acme")[0]["question"] == "Как режутся документы на куски?"


def test_statement_is_not_logged(home: Path, work: Path) -> None:
    prompt(home, work, "поправь тест")
    assert questions.history(cfg(home), "Acme") == []


def test_repeated_question_brings_the_earlier_answer(home: Path, work: Path) -> None:
    qid = questions.log_question(cfg(home), "Acme", "Как режутся документы на куски?")
    questions.answer(cfg(home), "Acme", qid, "По 512 токенов.", "ingest.md")
    result = prompt(home, work, "слушай, а как документы режутся на куски?")
    context = result["hookSpecificOutput"]["additionalContext"]
    assert "По 512 токенов." in context
    assert "re-verify" in context


def test_turn_start_is_remembered(home: Path, work: Path) -> None:
    prompt(home, work, "поправь тест")
    assert session.load(cfg(home), "s1")["turn_started"] == NOW


def test_high_five_hour_use_asks_spend_or_save(home: Path, work: Path) -> None:
    state = home / ".local/state/bedrock"
    state.mkdir(parents=True)
    (state / "limits.json").write_text(json.dumps({"five_hour": {"used_percentage": 82}}))
    context = prompt(home, work, "поправь тест")["hookSpecificOutput"]["additionalContext"]
    assert "spend or save" in context
    prompt(home, work, "экономим")
    after = prompt(home, work, "поправь тест")
    assert "spend or save" not in json.dumps(after)
