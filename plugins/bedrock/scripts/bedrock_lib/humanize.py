"""Which humanize setup a machine has: the personal skill's own hook, or the bundled one."""

from __future__ import annotations

import json
from pathlib import Path

PROFILE_FILE = "profile.md"


def personal_hook(claude_dir: Path) -> bool:
    """Whether claude-humanize-skill's prompt hook is in Claude Code's user settings."""
    for name in ("settings.json", "settings.local.json"):
        try:
            data = json.loads((claude_dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if isinstance(hooks, dict) and "draft_trigger" in json.dumps(hooks.get("UserPromptSubmit")):
            return True
    return False


def profile(home: Path) -> Path | None:
    """The voice profile the skill would read, or None when it falls back to the default voice."""
    for folder in (
        home / ".claude" / "skills" / "humanize" / "profile",
        home / ".config" / "humanize" / "profile",
    ):
        if (folder / PROFILE_FILE).is_file():
            return folder
    return None
