#!/usr/bin/env python3
"""Claude Code calls this for every hook event; the work is in scripts/bedrock_hooks."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

try:
    from bedrock_hooks.dispatch import bootstrap
except Exception as error:  # noqa: BLE001 - a broken install must refuse tools, not pass them
    if sys.argv[1:2] == ["PreToolUse"]:
        reason = f"bedrock guards could not load: {type(error).__name__}: {error}"
        decision = {"hookEventName": "PreToolUse", "permissionDecision": "deny"}
        print(json.dumps({"hookSpecificOutput": {**decision, "permissionDecisionReason": reason}}))
    sys.exit(0)

sys.exit(bootstrap())
