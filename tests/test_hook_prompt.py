import io
import json
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES
from bedrock_lib import questions
from bedrock_lib.config import load_user_config

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
    data = {"session_id": "s1", "cwd": str(work), "prompt": text}
    if source:
        data["source"] = source
    out = io.StringIO()
    dispatch.main(["UserPromptSubmit"], io.StringIO(json.dumps(data)), out, environ(home), RULES)
    return json.loads(out.getvalue() or "{}")


def cfg(home: Path):
    return load_user_config(environ(home))


@pytest.mark.parametrize(
    "text", ["запушь", "/bedrock:allow push", "/bedrock:unleash", "сегодня до талого", "экономим"]
)
def test_grant_and_spend_words_change_nothing(home: Path, work: Path, text: str) -> None:
    result = prompt(home, work, text)
    state = home / ".local/state/bedrock"
    assert not (state / "grants.json").exists()
    assert not (state / "spend.json").exists()
    assert "systemMessage" not in result
    assert "decision" not in result


def test_high_five_hour_use_adds_nothing(home: Path, work: Path) -> None:
    state = home / ".local/state/bedrock"
    state.mkdir(parents=True)
    (state / "limits.json").write_text(json.dumps({"five_hour": {"used_percentage": 99}}))
    assert prompt(home, work, "поправь тест") == {}


def test_question_is_logged(home: Path, work: Path) -> None:
    prompt(home, work, "Как режутся документы на куски?")
    assert questions.history(cfg(home), "Acme")[0]["question"] == "Как режутся документы на куски?"


def test_statement_is_not_logged(home: Path, work: Path) -> None:
    prompt(home, work, "поправь тест")
    assert questions.history(cfg(home), "Acme") == []


def test_pasted_question_is_not_the_owners(home: Path, work: Path) -> None:
    prompt(home, work, '<pasted_content id="1">Как режутся документы?</pasted_content>')
    assert questions.history(cfg(home), "Acme") == []


@pytest.mark.parametrize("source", ["loop_wakeup", "sdk"])
def test_only_the_owners_prompt_is_logged(home: Path, work: Path, source: str) -> None:
    prompt(home, work, "Как режутся документы на куски?", source=source)
    assert questions.history(cfg(home), "Acme") == []


def test_repeated_question_brings_the_earlier_answer(home: Path, work: Path) -> None:
    qid = questions.log_question(cfg(home), "Acme", "Как режутся документы на куски?")
    questions.answer(cfg(home), "Acme", qid, "По 512 токенов.", "ingest.md")
    result = prompt(home, work, "слушай, а как документы режутся на куски?")
    context = result["hookSpecificOutput"]["additionalContext"]
    assert "По 512 токенов." in context
    assert "re-verify" in context
