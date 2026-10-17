import io
import json
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES
from bedrock_lib import ledger, session
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


def hook(home: Path, event: str, data: dict) -> dict:
    out = io.StringIO()
    payload = {"session_id": "s1", "hook_event_name": event, **data}
    dispatch.main([event], io.StringIO(json.dumps(payload)), out, environ(home), RULES)
    return json.loads(out.getvalue() or "{}")


def spawn(home: Path, work: Path, prompt: str, kind: str = "inventory", **extra: object) -> str:
    tool_input = {"description": "d", "prompt": prompt, "subagent_type": kind, **extra}
    data = {"cwd": str(work), "tool_name": "Agent", "tool_input": tool_input, "tool_use_id": "t1"}
    result = hook(home, "PreToolUse", data)
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def start(home: Path, work: Path, agent: str, kind: str = "inventory") -> None:
    hook(home, "SubagentStart", {"cwd": str(work), "agent_id": agent, "agent_type": kind})


def limits(home: Path, five: float, week: float = 10) -> None:
    state = home / ".local/state/bedrock"
    state.mkdir(parents=True, exist_ok=True)
    data = {"five_hour": {"used_percentage": five}, "seven_day": {"used_percentage": week}}
    (state / "limits.json").write_text(json.dumps(data))


GOOD = (
    "Reason: a — reads 40 files the session will not need\n"
    "Task: list the ingest entry points\nDone when: every entry point has file:line\n"
    "Report: .bedrock/r1.md"
)
WRITE = "Task: fix the chunk overlap\nDone when: test_overlap passes\nCause: .bedrock/cause.md\n"


def test_agent_with_a_reason_passes(home: Path, work: Path) -> None:
    assert spawn(home, work, GOOD) == ""


def test_agent_without_a_reason_is_refused(home: Path, work: Path) -> None:
    assert "Reason:" in spawn(home, work, "look around the repo")


@pytest.mark.parametrize(
    ("knob", "kind", "refused"),
    [
        ("off", "inventory", True),
        ("read-only", "implementer", True),
        ("read-only", "inventory", False),
    ],
)
def test_project_agent_knob(home: Path, work: Path, knob: str, kind: str, refused: bool) -> None:
    settings = {"project": "Acme", "agents": knob}
    (work / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    assert bool(spawn(home, work, GOOD + "\nFiles: a.py\nCause: feature", kind=kind)) is refused


@pytest.mark.parametrize(("five", "week"), [(95, 10), (40, 90)])
def test_limits_stop_all_agents(home: Path, work: Path, five: float, week: float) -> None:
    limits(home, five, week)
    assert "limit" in spawn(home, work, GOOD)


def test_at_eighty_percent_only_review_runs_until_the_owner_chooses(home: Path, work: Path) -> None:
    limits(home, 82)
    assert "spend or save" in spawn(home, work, GOOD)
    assert spawn(home, work, GOOD, kind="diff-reviewer") == ""
    start(home, work, "r1", kind="diff-reviewer")
    stop(home, work, "r1", active=True)
    hook(
        home,
        "UserPromptSubmit",
        {"cwd": str(work), "prompt": "сегодня до талого", "source": "user"},
    )
    assert spawn(home, work, GOOD) == ""


def test_budget_of_three_agents_per_window_outside_a_plan(home: Path, work: Path) -> None:
    for index in range(3):
        assert spawn(home, work, GOOD) == ""
        start(home, work, f"a{index}")
        hook(
            home,
            "SubagentStop",
            {
                "cwd": str(work),
                "agent_id": f"a{index}",
                "agent_type": "inventory",
                "agent_transcript_path": "",
                "stop_hook_active": True,
            },
        )
    assert "budget" in spawn(home, work, GOOD)


def test_plan_budget_overrides_the_default(home: Path, work: Path) -> None:
    cfg = load_user_config(environ(home))
    session.update(cfg, "s1", {"agent_budget": 5})
    for index in range(4):
        assert spawn(home, work, GOOD) == ""
        start(home, work, f"a{index}")
        hook(
            home,
            "SubagentStop",
            {
                "cwd": str(work),
                "agent_id": f"a{index}",
                "agent_type": "inventory",
                "agent_transcript_path": "",
                "stop_hook_active": True,
            },
        )


def test_three_readers_at_once_and_one_when_the_window_is_half_used(home: Path, work: Path) -> None:
    for index in range(3):
        assert spawn(home, work, GOOD) == ""
        start(home, work, f"a{index}")
    cfg = load_user_config(environ(home))
    session.update(cfg, "s1", {"agent_budget": 10})
    assert "at once" in spawn(home, work, GOOD)


def test_one_writer_in_the_shared_checkout(home: Path, work: Path) -> None:
    brief = GOOD + "\nFiles: src/a.py\nCause: feature"
    assert spawn(home, work, brief, kind="implementer") == ""
    start(home, work, "w1", kind="implementer")
    assert "writer" in spawn(home, work, brief, kind="implementer")


def transcript(path: Path, context: int) -> str:
    usage = {"input_tokens": 1000, "cache_read_input_tokens": context - 1000, "output_tokens": 5}
    path.write_text(
        json.dumps({"type": "assistant", "message": {"id": "m", "usage": usage}}) + "\n"
    )
    return str(path)


def test_fork_rules(home: Path, work: Path, tmp_path: Path) -> None:
    small = transcript(tmp_path / "small.jsonl", 90_000)
    big = transcript(tmp_path / "big.jsonl", 200_000)
    fork = (
        "Reason: fork\nFork: rests on decisions made in this conversation, context 90k\n"
        "Task: try approach B\nDone when: B passes the suite\nReport: .bedrock/fork.md"
    )

    def try_fork(prompt: str, path: str) -> str:
        tool_input = {"description": "d", "prompt": prompt, "subagent_type": "fork"}
        data = {
            "cwd": str(work),
            "tool_name": "Agent",
            "tool_input": tool_input,
            "transcript_path": path,
        }
        result = hook(home, "PreToolUse", data)
        return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")

    assert "Fork:" in try_fork(fork.replace("Fork: rests", "Notes: rests"), small)
    assert "150k" in try_fork(fork, big)
    assert try_fork(fork, small) == ""
    start(home, work, "f1", kind="fork")
    assert "one fork" in try_fork(fork, small)


def test_agent_edits_only_its_own_files(home: Path, work: Path) -> None:
    brief = WRITE + "Reason: a\nFiles: src/a.py, src/b.py\nReport: .bedrock/r.md"
    spawn(home, work, brief, kind="implementer")
    start(home, work, "w1", kind="implementer")

    def edit(path: str) -> str:
        data = {
            "cwd": str(work),
            "tool_name": "Edit",
            "agent_id": "w1",
            "tool_input": {"file_path": path},
        }
        return (
            hook(home, "PreToolUse", data)
            .get("hookSpecificOutput", {})
            .get("permissionDecisionReason", "")
        )

    assert edit(str(work / "src" / "a.py")) == ""
    assert edit("src/b.py") == ""
    assert edit(str(work / ".bedrock" / "r.md")) == ""
    assert "not in its brief" in edit(str(work / "src" / "c.py"))
    assert "not in its brief" in edit(str(work / "src" / ".." / "secrets.py"))


def test_agent_without_a_brief_cannot_edit(home: Path, work: Path) -> None:
    data = {
        "cwd": str(work),
        "tool_name": "Write",
        "agent_id": "ghost",
        "tool_input": {"file_path": "x.py"},
    }
    reason = hook(home, "PreToolUse", data)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "brief" in reason


def test_main_session_edits_are_not_limited(home: Path, work: Path) -> None:
    data = {"cwd": str(work), "tool_name": "Edit", "tool_input": {"file_path": "anything.py"}}
    assert hook(home, "PreToolUse", data) == {}


def stop(
    home: Path,
    work: Path,
    agent: str,
    path: str = "",
    active: bool = False,
    tasks: list | None = None,
) -> dict:
    data = {
        "cwd": str(work),
        "agent_id": agent,
        "agent_type": "inventory",
        "agent_transcript_path": path,
        "stop_hook_active": active,
    }
    if tasks is not None:
        data["background_tasks"] = tasks
    return hook(home, "SubagentStop", data)


def test_agent_cannot_finish_with_background_commands_running(home: Path, work: Path) -> None:
    spawn(home, work, GOOD)
    start(home, work, "a1")
    (work / ".bedrock").mkdir()
    (work / ".bedrock" / "r1.md").write_text("done")
    result = stop(
        home, work, "a1", tasks=[{"id": "b1", "status": "running", "command": "npm test"}]
    )
    assert result["decision"] == "block"
    assert "npm test" in result["reason"]
    assert stop(home, work, "a1", tasks=[{"id": "b1", "status": "completed"}]) == {}


def test_agent_must_write_its_report(home: Path, work: Path) -> None:
    spawn(home, work, GOOD)
    start(home, work, "a1")
    result = stop(home, work, "a1")
    assert result["decision"] == "block"
    assert ".bedrock/r1.md" in result["reason"]
    assert stop(home, work, "a1", active=True) == {}


def test_finished_agent_goes_into_the_ledger(home: Path, work: Path, tmp_path: Path) -> None:
    spawn(home, work, GOOD + "\nEstimate: 300k", model="haiku")
    start(home, work, "a1")
    (work / ".bedrock").mkdir()
    (work / ".bedrock" / "r1.md").write_text("done")
    stop(home, work, "a1", path=transcript(tmp_path / "agent.jsonl", 20_000))
    records = ledger.records(load_user_config(environ(home)))
    assert len(records) == 1
    record = records[0]
    assert (record["role"], record["model"], record["reason"]) == ("inventory", "haiku", "a")
    assert record["estimate"] == 300000.0
    assert record["actual"] == pytest.approx(1000 + 19000 * 0.1 + 25)
    assert record["accepted"] is None


def test_stale_pending_and_active_agents_do_not_block(home: Path, work: Path) -> None:
    cfg = load_user_config(environ(home))
    agents = {
        "pending": [{"type": "inventory", "at": "2026-10-17T11:40:00Z"}],
        "active": {"x": {"type": "implementer", "at": "2026-10-17T08:00:00Z"}},
        "started": [],
    }
    session.update(cfg, "s1", {"agents": agents})
    assert spawn(home, work, GOOD + "\nFiles: a.py\nCause: feature", kind="implementer") == ""


@pytest.mark.parametrize("missing", ["Task:", "Done when:", "Report:"])
def test_brief_needs_task_done_when_and_report(home: Path, work: Path, missing: str) -> None:
    brief = "\n".join(line for line in GOOD.splitlines() if not line.startswith(missing))
    assert missing.rstrip(":") in spawn(home, work, brief)


@pytest.mark.parametrize("missing", ["Cause:", "Files:"])
def test_implementer_brief_needs_cause_and_files(home: Path, work: Path, missing: str) -> None:
    brief = GOOD + "\nFiles: src/a.py\nCause: feature"
    brief = "\n".join(line for line in brief.splitlines() if not line.startswith(missing))
    assert missing.rstrip(":") in spawn(home, work, brief, kind="implementer")


def test_spend_mode_shifts_the_agent_effort(home: Path, work: Path) -> None:
    def routed(prompt: str) -> dict:
        hook(home, "UserPromptSubmit", {"cwd": str(work), "prompt": prompt, "source": "user"})
        tool_input = {"description": "d", "prompt": GOOD, "subagent_type": "critic"}
        data = {"cwd": str(work), "tool_name": "Agent", "tool_input": tool_input}
        return hook(home, "PreToolUse", data).get("hookSpecificOutput", {})

    assert routed("сегодня до талого")["updatedInput"]["effort"] == "xhigh"
    assert routed("экономим")["updatedInput"]["effort"] == "medium"
    assert "updatedInput" not in routed("обычный режим")


def test_hitting_the_turn_cap_is_recorded(home: Path, work: Path, tmp_path: Path) -> None:
    spawn(home, work, GOOD, kind="critic")
    start(home, work, "c1", kind="critic")
    (work / ".bedrock").mkdir()
    (work / ".bedrock" / "r1.md").write_text("done")
    path = tmp_path / "critic.jsonl"
    usage = {"input_tokens": 10, "output_tokens": 1}
    lines = [
        json.dumps({"type": "assistant", "message": {"id": f"m{i}", "usage": usage}})
        for i in range(10)
    ]
    path.write_text("\n".join(lines) + "\n")
    data = {
        "cwd": str(work),
        "agent_id": "c1",
        "agent_type": "critic",
        "agent_transcript_path": str(path),
        "stop_hook_active": False,
    }
    hook(home, "SubagentStop", data)
    record = ledger.records(load_user_config(environ(home)))[-1]
    assert (record["turns"], record["cap_hit"]) == (10, True)
