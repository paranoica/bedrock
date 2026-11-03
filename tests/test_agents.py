import json
from pathlib import Path

import pytest
from bedrock_lib import agents, clock


def write_agent(
    root: Path,
    agent_id: str = "a1b2c3d4e5",
    session: str = "s1",
    lines: list[object] | None = None,
    meta: dict | None = None,
    folder: str = "-work-acme",
) -> Path:
    base = root / "projects" / folder / session / "subagents"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"agent-{agent_id}.jsonl"
    body = []
    for line in lines or []:
        body.append(line if isinstance(line, str) else json.dumps(line))
    path.write_text("\n".join(body) + "\n")
    if meta is not None:
        (base / f"agent-{agent_id}.meta.json").write_text(json.dumps(meta))
    return path


def turn(message_id: str, usage: dict, ts: str, model: str = "claude-opus-5-5") -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "cwd": "/work/acme",
        "message": {"id": message_id, "model": model, "usage": usage},
    }


FIRST = {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 2}
SECOND = {
    "input_tokens": 0,
    "cache_read_input_tokens": 2000,
    "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 40},
    "cache_creation_input_tokens": 140,
    "output_tokens": 50,
}


def test_spend_weights_and_counts_a_request_once(tmp_path: Path) -> None:
    path = write_agent(
        tmp_path,
        lines=[
            turn("m1", FIRST, "2026-11-01T10:00:00Z"),
            turn("m1", FIRST, "2026-11-01T10:00:01Z"),
            turn("m2", SECOND, "2026-11-01T10:06:00Z"),
        ],
    )
    run = agents.read_run(path, "s1")
    # m1: 10 + 1000*0.1 + 2*5 = 120; m2: 2000*0.1 + 100*1.25 + 40*2 + 50*5 = 655
    assert run.turns == 2
    assert run.weighted == pytest.approx(775.0)
    assert run.tokens == {
        "input": 10,
        "cache_5m": 100,
        "cache_1h": 40,
        "cache_read": 3000,
        "output": 52,
    }
    assert run.minutes == pytest.approx(6.0)
    assert run.cwd == "/work/acme"
    assert run.model == "claude-opus-5-5"


def test_old_usage_without_the_split_counts_as_five_minute_cache(tmp_path: Path) -> None:
    usage = {"cache_creation_input_tokens": 100, "output_tokens": 0}
    run = agents.read_run(
        write_agent(tmp_path, lines=[turn("m1", usage, "2026-11-01T10:00:00Z")]), "s1"
    )
    assert run.tokens["cache_5m"] == 100
    assert run.weighted == pytest.approx(125.0)


def test_synthetic_messages_and_other_records_cost_nothing(tmp_path: Path) -> None:
    lines = [
        turn("s", FIRST, "2026-11-01T10:00:00Z", model="<synthetic>"),
        {"type": "user", "timestamp": "2026-11-01T10:00:02Z", "message": {"content": "x"}},
        {"type": "assistant", "timestamp": "2026-11-01T10:00:03Z", "message": "not a dict"},
    ]
    run = agents.read_run(write_agent(tmp_path, lines=lines), "s1")
    assert run.turns == 0
    assert run.weighted == 0.0
    assert run.minutes == pytest.approx(3 / 60)


def test_broken_lines_are_counted_not_fatal(tmp_path: Path) -> None:
    lines = ['{"type": "assistant"', "[1, 2]", turn("m1", FIRST, "2026-11-01T10:00:00Z")]
    run = agents.read_run(write_agent(tmp_path, lines=lines), "s1")
    assert run.broken_lines == 2
    assert run.turns == 1


def test_empty_transcript_is_an_empty_run(tmp_path: Path) -> None:
    run = agents.read_run(write_agent(tmp_path, lines=[]), "s1")
    assert (run.turns, run.weighted, run.started, run.minutes) == (0, 0.0, None, 0.0)


def test_scan_reads_meta_and_reports_what_it_could_not(tmp_path: Path) -> None:
    write_agent(
        tmp_path,
        "a1b2c3d4e5",
        lines=[turn("m1", FIRST, "2026-11-01T10:00:00Z")],
        meta={"agentType": "bedrock:reviewer", "description": "review b1", "finished": True},
    )
    write_agent(
        tmp_path, "f9f9f9f9f9", lines=["garbage", turn("m2", FIRST, "2026-11-02T10:00:00Z")]
    )
    found = agents.scan(tmp_path)
    kinds = sorted(run.kind for run in found.runs)
    assert kinds == ["bedrock:reviewer", "unknown"]
    assert found.files == 2
    assert found.without_meta == 1
    assert found.broken_lines == 1
    text = agents.coverage(found)
    assert "read 2 agent transcripts" in text
    assert "1 without a meta file" in text
    assert "1 unreadable lines or token counts skipped" in text


def test_scan_since_keeps_runs_from_that_moment(tmp_path: Path) -> None:
    write_agent(tmp_path, "aaaaaaaaaa", lines=[turn("m1", FIRST, "2026-10-31T23:59:59Z")])
    write_agent(tmp_path, "bbbbbbbbbb", lines=[turn("m1", FIRST, "2026-11-01T00:00:00Z")])
    write_agent(tmp_path, "cccccccccc", lines=[])
    found = agents.scan(tmp_path, since=clock.parse("2026-11-01"))
    assert [run.agent_id for run in found.runs] == ["bbbbbbbbbb"]
    assert found.files == 3


def test_scan_of_a_missing_folder_reads_nothing(tmp_path: Path) -> None:
    found = agents.scan(tmp_path / "nowhere")
    assert (found.files, found.runs) == (0, [])
    assert agents.coverage(found).startswith("read 0 agent transcripts")


def test_report_groups_costliest_first(tmp_path: Path) -> None:
    write_agent(
        tmp_path,
        "aaaaaaaaaa",
        lines=[turn("m1", FIRST, "2026-11-01T10:00:00Z")],
        meta={"agentType": "bedrock:critic"},
    )
    write_agent(
        tmp_path,
        "bbbbbbbbbb",
        lines=[turn("m1", SECOND, "2026-11-02T10:00:00Z")],
        meta={"agentType": "general-purpose"},
    )
    found = agents.scan(tmp_path)
    rows = agents.report(found, "role", lambda run: "acme").splitlines()
    assert rows[1].startswith("general-purpose")
    assert rows[2].startswith("bedrock:critic")
    days = agents.report(found, "day", lambda run: "acme")
    assert "2026-11-01" in days and "2026-11-02" in days
    assert agents.report(found, "project", lambda run: "acme").splitlines()[1].startswith("acme")


def test_find_returns_the_agent_of_that_session_only(tmp_path: Path) -> None:
    write_agent(
        tmp_path,
        "a1b2c3d4e5",
        session="s1",
        lines=[turn("m1", FIRST, "2026-11-01T10:00:00Z")],
        meta={"agentType": "bedrock:reviewer", "finished": True},
    )
    run = agents.find(tmp_path, "s1", "a1b2c3d4e5")
    assert run is not None and run.kind == "bedrock:reviewer" and run.finished is True
    assert agents.find(tmp_path, "s2", "a1b2c3d4e5") is None
    assert agents.find(tmp_path, "s1", "0000000000") is None


@pytest.mark.parametrize("agent_id", ["../x", "a*", "", "A1B2C3D4E5", "a1/b2c3d4"])
def test_find_refuses_odd_agent_ids(tmp_path: Path, agent_id: str) -> None:
    write_agent(tmp_path, "a1b2c3d4e5", lines=[])
    assert agents.find(tmp_path, "s1", agent_id) is None


@pytest.mark.parametrize("session", ["*", "../s1", "s1/x", ""])
def test_find_refuses_odd_session_ids(tmp_path: Path, session: str) -> None:
    write_agent(tmp_path, "a1b2c3d4e5", lines=[])
    assert agents.find(tmp_path, session, "a1b2c3d4e5") is None


@pytest.mark.parametrize(
    ("kind", "reviewer"),
    [
        ("bedrock:reviewer", True),
        ("bedrock:security-reviewer", True),
        ("general-purpose", False),
        ("bedrock:critic", False),
        ("unknown", False),
    ],
)
def test_reviewer_is_told_by_agent_type(kind: str, reviewer: bool) -> None:
    run = agents.Run(agent_id="a1b2c3d4e5", session="s1", path=Path("x"), kind=kind)
    assert agents.is_reviewer(run) is reviewer


def test_claude_dir_follows_the_config_variable(tmp_path: Path) -> None:
    assert agents.claude_dir({"CLAUDE_CONFIG_DIR": str(tmp_path)}) == tmp_path
    assert agents.claude_dir({}) == Path.home() / ".claude"


@pytest.mark.parametrize("odd", ["lots", [1], {"a": 1}, -5, True, 1.5])
def test_odd_usage_numbers_are_skipped_and_counted(tmp_path: Path, odd: object) -> None:
    usage = {"output_tokens": odd, "input_tokens": 10}
    write_agent(tmp_path, lines=[turn("m1", usage, "2026-11-01T10:00:00Z")])
    found = agents.scan(tmp_path)
    run = found.runs[0]
    assert run.tokens["output"] == 0 and run.tokens["input"] == 10
    assert found.broken_lines == 1
