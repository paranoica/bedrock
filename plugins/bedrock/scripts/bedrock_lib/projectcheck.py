"""Check a workspace's `.claude/bedrock.json` before anything relies on it (K1, D047)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import commands
from .config import SAFE_NAME

PACKS = Path(__file__).resolve().parents[2] / "packs"
AGENT_MODES = {"full", "read-only", "off"}
LIST_KEYS = {
    "critical_zones": "path globs",
    "packs": "pack names",
}
SECTION_LISTS = {
    "kb": ("roots",),
    "leaks": ("allow", "ignore"),
    "checks": ("allow_hosts", "ignore"),
}
SECTION_KEYS = {
    "kb": {"roots"},
    "leaks": {"allow", "ignore", "gitleaks"},
    "checks": {"allow_hosts", "ignore", "file_lines", "function_lines", "commit_format"},
    "bench": {"answer_key"},
}
KNOWN = {"project", "commands", "compact_window", "agents", "bench", *LIST_KEYS, *SECTION_LISTS}


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


def _commands(data: dict[str, Any]) -> list[str]:
    raw = data.get("commands")
    if not isinstance(raw, dict) or not raw:
        return ["commands: none set; derive them from the project's files and run each once"]
    found = []
    for name, spec in raw.items():
        try:
            commands._parse(name, spec)
        except commands.CommandError as error:
            found.append(f"commands: {error}")
    return found


def _sections(data: dict[str, Any]) -> list[str]:
    found = []
    for section, keys in SECTION_LISTS.items():
        value = data.get(section)
        if value is None:
            continue
        if not isinstance(value, dict):
            found.append(f"{section}: must be an object")
            continue
        found += [
            f"{section}.{key}: must be a list of strings"
            for key in keys
            if key in value and not _strings(value[key])
        ]
        found += [
            f"{section}.{key}: unknown key, a typo or a setting bedrock does not read"
            for key in value
            if key not in SECTION_KEYS[section]
        ]
    return found


def check(data: dict[str, Any], packs: Path = PACKS) -> list[str]:
    """Every problem in the settings, each naming its key and the fix."""
    found = []
    name = data.get("project")
    if not isinstance(name, str) or not SAFE_NAME.match(name):
        found.append(f"project: '{name}' is not a safe folder name")
    found += _commands(data)
    for key, what in LIST_KEYS.items():
        if key in data and not _strings(data[key]):
            found.append(f"{key}: must be a list of {what}")
    if _strings(data.get("packs")):
        found += [
            f"packs: no pack '{p}' (have: {', '.join(sorted(x.stem for x in packs.glob('*.md')))})"
            for p in data["packs"]
            if not SAFE_NAME.match(p) or not (packs / f"{p}.md").is_file()
        ]
    agents = data.get("agents", "full")
    if not isinstance(agents, str) or agents not in AGENT_MODES:
        found.append(f"agents: one of {', '.join(sorted(AGENT_MODES))}")
    window = data.get("compact_window")
    if window is not None and (
        isinstance(window, bool) or not isinstance(window, int) or not 100000 <= window <= 1000000
    ):
        found.append("compact_window: an integer from 100000 to 1000000")
    found += _sections(data)
    bench = data.get("bench")
    if bench is not None and not (
        isinstance(bench, dict) and isinstance(bench.get("answer_key"), str) and bench["answer_key"]
    ):
        found.append("bench: an object with answer_key, the path of the folder agents never read")
    found += [
        f"unknown key '{key}': a typo, or a setting bedrock does not read"
        for key in data
        if key not in KNOWN
    ]
    return found
