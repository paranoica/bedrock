import json
from pathlib import Path

import pytest
from bedrock_lib import backlog
from bedrock_lib.config import UserConfig


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(
        days_dir=tmp_path / "days", state_dir=tmp_path / "state", memory_bank_dir=tmp_path / "kb"
    )


def add(cfg: UserConfig, title: str, **fields: object) -> str:
    return backlog.add(cfg, "Acme", {"title": title, "priority": "P2", "risk": "R2", **fields})


def test_add_assigns_ids_and_defaults(cfg: UserConfig) -> None:
    first = add(cfg, "dedupe search")
    second = add(cfg, "wire into query", depends=[first])
    assert (first, second) == ("T1", "T2")
    task = backlog.get(cfg, "Acme", "T2")
    assert task["status"] == "todo"
    assert task["depends"] == ["T1"]
    assert task["claimed_by"] is None


@pytest.mark.parametrize(
    "bad",
    [
        {"title": ""},
        {"priority": "P4"},
        {"risk": "R0"},
        {"depends": ["T9"]},
        {"estimate_min": -5},
        {"estimate_min": True},
        {"files": "a.py"},
        {"night_ok": "yes"},
        {"who": "intern"},
    ],
)
def test_add_rejects_bad_fields(cfg: UserConfig, bad: dict[str, object]) -> None:
    fields = {"title": "x", "priority": "P2", "risk": "R2", **bad}
    with pytest.raises(backlog.BacklogError):
        backlog.add(cfg, "Acme", fields)
    assert backlog.tasks(cfg, "Acme") == []


def test_who_is_session_or_a_named_agent_model(cfg: UserConfig) -> None:
    add(cfg, "a", who="session")
    add(cfg, "b", who="agent:sonnet")
    with pytest.raises(backlog.BacklogError):
        add(cfg, "c", who="agent:")


def test_next_takes_priority_then_order_and_waits_for_dependencies(cfg: UserConfig) -> None:
    low = add(cfg, "low", priority="P3")
    base = add(cfg, "base", priority="P1")
    add(cfg, "after base", priority="P0", depends=[base])
    assert backlog.next_task(cfg, "Acme")["id"] == base
    backlog.claim(cfg, "Acme", base, "s1")
    backlog.set_status(cfg, "Acme", base, "done")
    assert backlog.next_task(cfg, "Acme")["title"] == "after base"
    assert low == "T1"


def test_next_skips_tasks_claimed_by_another_session(cfg: UserConfig) -> None:
    first = add(cfg, "first")
    add(cfg, "second")
    backlog.claim(cfg, "Acme", first, "s1")
    assert backlog.next_task(cfg, "Acme")["title"] == "second"


def test_claim_refuses_a_task_held_by_another_session(cfg: UserConfig) -> None:
    task = add(cfg, "x")
    backlog.claim(cfg, "Acme", task, "s1")
    backlog.claim(cfg, "Acme", task, "s1")
    with pytest.raises(backlog.BacklogError, match="s1"):
        backlog.claim(cfg, "Acme", task, "s2")
    assert backlog.get(cfg, "Acme", task)["status"] == "doing"


def test_claim_refuses_unmet_dependencies(cfg: UserConfig) -> None:
    base = add(cfg, "base")
    after = add(cfg, "after", depends=[base])
    with pytest.raises(backlog.BacklogError, match=base):
        backlog.claim(cfg, "Acme", after, "s1")


def test_night_queue_only_holds_tasks_marked_ok_at_night(cfg: UserConfig) -> None:
    add(cfg, "risky", priority="P0")
    add(cfg, "safe", night_ok=True)
    assert backlog.next_task(cfg, "Acme", night=True)["title"] == "safe"


def test_done_needs_dependencies_done(cfg: UserConfig) -> None:
    base = add(cfg, "base")
    after = add(cfg, "after", depends=[base])
    with pytest.raises(backlog.BacklogError):
        backlog.set_status(cfg, "Acme", after, "done")


def test_blocked_needs_a_reason_and_releases_the_claim(cfg: UserConfig) -> None:
    task = add(cfg, "x")
    backlog.claim(cfg, "Acme", task, "s1")
    with pytest.raises(backlog.BacklogError):
        backlog.set_status(cfg, "Acme", task, "blocked")
    backlog.set_status(cfg, "Acme", task, "blocked", note="needs VPN login from the owner")
    blocked = backlog.get(cfg, "Acme", task)
    assert blocked["claimed_by"] is None
    assert blocked["notes"][-1].endswith("needs VPN login from the owner")


def test_unknown_task_and_state_are_errors(cfg: UserConfig) -> None:
    add(cfg, "x")
    with pytest.raises(backlog.BacklogError):
        backlog.set_status(cfg, "Acme", "T9", "done")
    with pytest.raises(backlog.BacklogError):
        backlog.set_status(cfg, "Acme", "T1", "finished")


def test_render_is_generated_and_validate_catches_a_hand_edit(cfg: UserConfig) -> None:
    add(cfg, "dedupe search", priority="P1", estimate_min=40)
    markdown = (cfg.memory_bank_dir / "Acme" / "backlog.md").read_text()
    assert "GENERATED" in markdown
    assert "T1" in markdown and "dedupe search" in markdown and "P1" in markdown
    assert backlog.validate(cfg, "Acme") == []
    path = cfg.memory_bank_dir / "Acme" / "backlog.json"
    data = json.loads(path.read_text())
    data["tasks"][0]["status"] = "done"
    path.write_text(json.dumps(data))
    problems = backlog.validate(cfg, "Acme")
    assert any("backlog.md" in problem for problem in problems)


def test_validate_finds_cycles_and_dangling_dependencies(cfg: UserConfig) -> None:
    add(cfg, "a")
    add(cfg, "b", depends=["T1"])
    path = cfg.memory_bank_dir / "Acme" / "backlog.json"
    data = json.loads(path.read_text())
    data["tasks"][0]["depends"] = ["T2"]
    data["tasks"][1]["depends"] = ["T1", "T7"]
    path.write_text(json.dumps(data))
    problems = " ".join(backlog.validate(cfg, "Acme"))
    assert "cycle" in problems
    assert "T7" in problems


def test_empty_backlog_has_no_next_task(cfg: UserConfig) -> None:
    assert backlog.next_task(cfg, "Acme") is None
    assert backlog.validate(cfg, "Acme") == []


def test_unsafe_project_is_rejected(cfg: UserConfig) -> None:
    with pytest.raises(backlog.BacklogError):
        backlog.tasks(cfg, "../x")
