import io
import json
import re
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES

HOOKS = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "hooks" / "hooks.json"


def spawn(tmp_path: Path, tool: str, tool_input: dict, agent: bool = False) -> dict:
    data = {"session_id": "s1", "cwd": str(tmp_path), "tool_name": tool, "tool_input": tool_input}
    if agent:
        data["agent_id"] = "a1b2c3d4e5"
    out = io.StringIO()
    env = {"HOME": str(tmp_path), "BEDROCK_NOW": "2026-11-07T12:00:00Z", "PATH": "/usr/bin:/bin"}
    dispatch.main(["PreToolUse"], io.StringIO(json.dumps(data)), out, env, RULES)
    return json.loads(out.getvalue() or "{}")


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Agent", {"subagent_type": "general-purpose", "prompt": "audit the web app"}),
        ("Agent", {"prompt": "audit the web app"}),
        ("Agent", {"subagent_type": "", "prompt": "x"}),
        ("Task", {"subagent_type": "general-purpose", "prompt": "x"}),
    ],
)
def test_general_purpose_gets_the_roles_and_still_starts(
    tmp_path: Path, tool: str, tool_input: dict
) -> None:
    for agent in (False, True):
        result = spawn(tmp_path, tool, tool_input, agent)
        specific = result["hookSpecificOutput"]
        assert "permissionDecision" not in specific
        assert "updatedInput" not in specific
        text = specific["additionalContext"]
        assert "bedrock:inventory" in text and "bedrock:reviewer" in text


@pytest.mark.parametrize("kind", ["bedrock:reviewer", "bedrock:inventory", "Explore", "fork"])
def test_a_named_role_gets_nothing(tmp_path: Path, kind: str) -> None:
    assert spawn(tmp_path, "Agent", {"subagent_type": kind, "prompt": "x"}) == {}


def test_other_tools_get_nothing(tmp_path: Path) -> None:
    assert spawn(tmp_path, "Bash", {"command": "ls"}) == {}


def test_the_hook_is_called_for_agent_spawns() -> None:
    matcher = json.loads(HOOKS.read_text())["hooks"]["PreToolUse"][0]["matcher"]
    for tool in ("Agent", "Task", "Bash"):
        assert re.fullmatch(matcher, tool), tool
    assert not re.fullmatch(matcher, "Edit")
