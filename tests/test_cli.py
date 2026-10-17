import json
import subprocess
import sys
from pathlib import Path

import bedrock_cli
import pytest

BIN = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "bin" / "bedrock"


@pytest.fixture(autouse=True)
def no_desktop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No notify-send on PATH, so no test can raise a real popup on the owner's screen.
    empty = tmp_path / "no-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def workspace(home: Path) -> Path:
    root = home / "work" / "app"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "bedrock.json").write_text('{"project": "Acme"}')
    (root / "src").mkdir()
    return root


def env_at(home: Path, now: str) -> dict[str, str]:
    return {"HOME": str(home), "BEDROCK_NOW": now}


def run(
    capsys: pytest.CaptureFixture[str], argv: list[str], env: dict[str, str], cwd: Path
) -> tuple[int, str, str]:
    code = bedrock_cli.main(argv, env=env, cwd=cwd)
    out, err = capsys.readouterr()
    return code, out, err


def test_log_and_minutes_use_the_workspace_project(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    cwd = workspace / "src"
    assert (
        run(capsys, ["log", "taken", "--block", "T1"], env_at(home, "2026-10-17T12:00:00Z"), cwd)[0]
        == 0
    )
    assert (
        run(capsys, ["log", "closed", "--block", "T1"], env_at(home, "2026-10-17T12:45:00Z"), cwd)[
            0
        ]
        == 0
    )
    code, out, _ = run(capsys, ["minutes", "T1"], env_at(home, "2026-10-17T13:00:00Z"), cwd)
    assert code == 0
    assert out.strip() == "45"
    assert (home / "projects-days" / "Acme" / "2026-10-17" / "log.jsonl").exists()


def test_minutes_open_counts_to_now(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    run(capsys, ["log", "taken", "--block", "T1"], env_at(home, "2026-10-17T12:00:00Z"), workspace)
    code, out, _ = run(
        capsys, ["minutes", "T1", "--open"], env_at(home, "2026-10-17T12:30:00Z"), workspace
    )
    assert (code, out.strip()) == (0, "30")


def test_no_project_is_an_error(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    code, out, err = run(capsys, ["minutes", "T1"], env_at(home, "2026-10-17T12:00:00Z"), home)
    assert code == 1
    assert out == ""
    assert err.startswith("bedrock: ")


def test_project_flag_works_outside_a_workspace(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    code, out, _ = run(
        capsys, ["minutes", "T1", "--project", "Other"], env_at(home, "2026-10-17T12:00:00Z"), home
    )
    assert (code, out.strip()) == (0, "0")


def test_bad_event_is_an_error_not_a_traceback(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys,
        ["log", "finished", "--block", "T1"],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 1
    assert "unknown event" in err
    assert "Traceback" not in err


def test_ledger_add_and_summary(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    entry = {
        "project": "Acme",
        "role": "critic",
        "model": "opus",
        "reason": "b",
        "estimate": 500000,
        "actual": 420000,
        "turns": 12,
        "cap_hit": False,
        "accepted": True,
    }
    env = env_at(home, "2026-10-17T12:00:00Z")
    assert run(capsys, ["ledger", "add", json.dumps(entry)], env, workspace)[0] == 0
    code, out, _ = run(capsys, ["ledger", "summary"], env, workspace)
    assert code == 0
    assert json.loads(out)["critic"]["actual"] == 420000.0


def test_ledger_add_rejects_broken_json(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys, ["ledger", "add", "{nope"], env_at(home, "2026-10-17T12:00:00Z"), workspace
    )
    assert code == 1
    assert err.startswith("bedrock: ")


def test_ledger_spend_reads_a_transcript(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    transcript = home / "t.jsonl"
    usage = {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 2}
    transcript.write_text(
        json.dumps({"type": "assistant", "message": {"id": "m1", "usage": usage}}) + "\n"
    )
    code, out, _ = run(
        capsys,
        ["ledger", "spend", str(transcript)],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 0
    assert json.loads(out) == {
        "weighted": 120.0,
        "turns": 1,
        "start_context": 1010,
        "peak_context": 1010,
    }


def test_question_log_answer_similar(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(
        capsys, ["question", "log", "How are documents split into chunks?"], env, workspace
    )
    qid = out.strip()
    assert code == 0 and len(qid) == 12
    assert (
        run(
            capsys,
            ["question", "answer", qid, "512 tokens", "--source", "ingest.md"],
            env,
            workspace,
        )[0]
        == 0
    )
    code, out, _ = run(
        capsys, ["question", "similar", "how do we split documents into chunks"], env, workspace
    )
    hits = json.loads(out)
    assert hits[0]["answer"] == "512 tokens"
    assert hits[0]["source"] == "ingest.md"
    assert hits[0]["score"] > 0.5


def test_answer_to_unknown_question_fails(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys,
        ["question", "answer", "nope", "x", "--source", "y"],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 1
    assert "no question" in err


def test_notify_prints_the_decision(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, out, _ = run(
        capsys, ["notify", "p0", "down", "api is down", "--action", "ok=OK"], env, workspace
    )
    result = json.loads(out)
    assert code == 0
    assert result["popup"] is False
    assert result["shown"] is False
    assert result["phone"] is True
    assert result["reason"] == "no notify-send"
    assert result["action"] is None


def test_notify_rejects_a_malformed_button(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, _, err = run(
        capsys, ["notify", "question", "t", "b", "--action", "nolabel"], env, workspace
    )
    assert code == 1
    assert "key=Label" in err


def test_bin_entry_point_runs(home: Path) -> None:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "BEDROCK_NOW": "2026-10-17T12:00:00Z"}
    completed = subprocess.run(
        [sys.executable, str(BIN), "minutes", "T1", "--project", "X"],
        env=env,
        cwd=home,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0"


def test_ledger_summary_with_a_bad_since_is_an_error(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["ledger", "summary", "--since", "yesterday"], env, workspace)
    assert code == 1
    assert err.startswith("bedrock: ")


def test_notify_accepts_a_timeout(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, out, _ = run(capsys, ["notify", "question", "t", "b", "--timeout", "30"], env, workspace)
    assert code == 0
    assert json.loads(out)["reason"] == "no notify-send"
