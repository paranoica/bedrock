import io
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_hooks import core, dispatch

ENTRY = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "hooks" / "dispatch.py"


def environ(tmp_path: Path) -> dict[str, str]:
    return {"HOME": str(tmp_path), "BEDROCK_NOW": "2026-10-17T12:00:00Z"}


def call(tmp_path: Path, event: str, data: dict, rules: list[core.Rule]) -> dict:
    out = io.StringIO()
    data = {"cwd": str(tmp_path), "session_id": "s1", **data}
    code = dispatch.main([event], io.StringIO(json.dumps(data)), out, environ(tmp_path), rules)
    assert code == 0
    return json.loads(out.getvalue() or "{}")


def rule(kind: str, verdict: core.Verdict | None = None, crash: bool = False) -> core.Rule:
    def check(event: core.Event, env: core.Env) -> core.Verdict | None:
        if crash:
            raise RuntimeError("boom")
        return verdict

    return core.Rule("demo", frozenset({"PreToolUse", "Stop", "UserPromptSubmit"}), kind, check)


TOOL = {"tool_name": "Bash", "tool_input": {"command": "ls"}}


def test_denial_becomes_a_pretooluse_deny(tmp_path: Path) -> None:
    result = call(tmp_path, "PreToolUse", TOOL, [rule(core.GUARD, core.Verdict(deny="no"))])
    specific = result["hookSpecificOutput"]
    assert specific["permissionDecision"] == "deny"
    assert specific["permissionDecisionReason"] == "no"


def test_crashing_guard_refuses(tmp_path: Path) -> None:
    result = call(tmp_path, "PreToolUse", TOOL, [rule(core.GUARD, crash=True)])
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "could not verify" in result["hookSpecificOutput"]["permissionDecisionReason"]


def test_crashing_helper_passes_and_is_logged(tmp_path: Path) -> None:
    result = call(tmp_path, "PreToolUse", TOOL, [rule(core.HELPER, crash=True)])
    assert result == {}
    log = tmp_path / ".local/state/bedrock/hook-errors.jsonl"
    assert "boom" in log.read_text()


def test_passing_rules_print_nothing(tmp_path: Path) -> None:
    assert call(tmp_path, "PreToolUse", TOOL, [rule(core.GUARD, None)]) == {}


def test_stop_block_and_context(tmp_path: Path) -> None:
    verdict = core.Verdict(block="next task: T2", context="note")
    result = call(tmp_path, "Stop", {"stop_hook_active": False}, [rule(core.HELPER, verdict)])
    assert result["decision"] == "block"
    assert result["reason"] == "next task: T2"


def test_updated_input_without_a_permission_decision(tmp_path: Path) -> None:
    verdict = core.Verdict(updated_input={"model": "sonnet"})
    result = call(tmp_path, "PreToolUse", TOOL, [rule(core.HELPER, verdict)])
    assert result["hookSpecificOutput"]["updatedInput"] == {"model": "sonnet"}
    assert "permissionDecision" not in result["hookSpecificOutput"]


def test_denial_wins_over_updated_input(tmp_path: Path) -> None:
    rules = [
        rule(core.GUARD, core.Verdict(deny="no")),
        rule(core.HELPER, core.Verdict(updated_input={})),
    ]
    result = call(tmp_path, "PreToolUse", TOOL, rules)
    assert "updatedInput" not in result["hookSpecificOutput"]


def test_rules_for_other_events_do_not_run(tmp_path: Path) -> None:
    only_stop = core.Rule("s", frozenset({"Stop"}), core.GUARD, lambda e, n: core.Verdict(deny="x"))
    assert call(tmp_path, "PreToolUse", TOOL, [only_stop]) == {}


def test_broken_input_refuses_tools(tmp_path: Path) -> None:
    out = io.StringIO()
    dispatch.main(["PreToolUse"], io.StringIO("not json"), out, environ(tmp_path), [])
    assert json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_broken_input_passes_other_events(tmp_path: Path) -> None:
    out = io.StringIO()
    dispatch.main(["Stop"], io.StringIO("not json"), out, environ(tmp_path), [])
    assert out.getvalue() in ("", "{}")


def test_off_switch_disables_everything(tmp_path: Path) -> None:
    out = io.StringIO()
    env = {**environ(tmp_path), "BEDROCK_HOOKS": "off"}
    data = json.dumps({"cwd": str(tmp_path), **TOOL})
    dispatch.main(
        ["PreToolUse"], io.StringIO(data), out, env, [rule(core.GUARD, core.Verdict(deny="x"))]
    )
    assert out.getvalue() == ""


def test_broken_owner_config_refuses_tools(tmp_path: Path) -> None:
    config = tmp_path / "bad.json"
    config.write_text('{"rollover_hour": 99}')
    out = io.StringIO()
    env = {**environ(tmp_path), "BEDROCK_CONFIG": str(config)}
    data = json.dumps({"cwd": str(tmp_path), **TOOL})
    dispatch.main(["PreToolUse"], io.StringIO(data), out, env, [])
    assert json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("event", ["PreToolUse", "Stop"])
def test_entry_script_runs_end_to_end(tmp_path: Path, event: str) -> None:
    data = {"cwd": str(tmp_path), "session_id": "s1", "hook_event_name": event, **TOOL}
    completed = subprocess.run(
        [sys.executable, str(ENTRY), event],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        env={**environ(tmp_path), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""


def test_entry_script_refuses_when_bedrock_cannot_load(tmp_path: Path) -> None:
    broken = tmp_path / "plugin"
    (broken / "hooks").mkdir(parents=True)
    (broken / "scripts" / "bedrock_hooks").mkdir(parents=True)
    (broken / "scripts" / "bedrock_hooks" / "__init__.py").write_text("raise ImportError('gone')\n")
    (broken / "hooks" / "dispatch.py").write_text(ENTRY.read_text())
    completed = subprocess.run(
        [sys.executable, str(broken / "hooks" / "dispatch.py"), "PreToolUse"],
        input="{}",
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_every_registered_rule_fails_according_to_its_class(tmp_path: Path) -> None:
    from bedrock_hooks.registry import RULES
    from bedrock_lib.config import UserConfig

    names = [r.name for r in RULES]
    assert len(names) == len(set(names))
    env = core.Env(UserConfig(state_dir=tmp_path / "s"), datetime.now(UTC), {}, tmp_path)

    def broken(event: core.Event, env: core.Env) -> core.Verdict:
        raise RuntimeError("boom")

    for rule in RULES:
        assert rule.kind in (core.GUARD, core.HELPER)
        crashing = core.Rule(rule.name, rule.events, rule.kind, broken)
        event = core.Event(sorted(rule.events)[0], {})
        outcome = core.evaluate(event, [crashing], env)
        assert bool(outcome.denials) is (rule.kind == core.GUARD), rule.name
        assert outcome.blocks == []


def test_undecodable_text_in_a_verdict_still_gives_valid_json(tmp_path: Path) -> None:
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="utf-8")
    data = json.dumps({"cwd": str(tmp_path), "session_id": "s1"})
    odd = rule(core.HELPER, core.Verdict(block="file caf\udce9.py changed"))
    assert dispatch.main(["Stop"], io.StringIO(data), out, environ(tmp_path), [odd]) == 0
    out.flush()
    result = json.loads(raw.getvalue().decode("utf-8"))
    assert result["decision"] == "block" and "caf" in result["reason"]
