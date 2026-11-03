#!/usr/bin/env python3
"""Claude Code calls this for every hook event; the work is in scripts/bedrock_hooks."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
GATED = re.compile(r"\bgh\b.*\bpr\b.*\b(?:create|merge)\b", re.S)

try:
    from bedrock_hooks.dispatch import bootstrap
except Exception as error:  # noqa: BLE001 - a broken install refuses only gated gh pr calls
    if sys.argv[1:2] == ["PreToolUse"] and GATED.search(sys.stdin.read()):
        reason = f"bedrock review gate could not load: {type(error).__name__}: {error}"
        decision = {"hookEventName": "PreToolUse", "permissionDecision": "deny"}
        print(json.dumps({"hookSpecificOutput": {**decision, "permissionDecisionReason": reason}}))
    sys.exit(0)

sys.exit(bootstrap())
