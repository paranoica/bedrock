#!/usr/bin/env bash
# genesis preflight — capability probe. Announces mode (full|degraded); NEVER aborts.
# Usage: preflight.sh [repo_root]   ->  prints a JSON capability report.
set -u
have() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }

ROOT="${1:-.}"
GIT=$( [ -d "$ROOT/.git" ] && echo true || echo false )
PY=$(have python3)
NODE=$(have node)

# Sibling skills in the Claude Code layout: .claude/skills/{genesis,design-creator,code-review}
SKILLS_DIR="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd || echo "")"
DC=$( [ -n "$SKILLS_DIR" ] && [ -f "$SKILLS_DIR/design-creator/SKILL.md" ] && echo true || echo false )
CR=$( [ -n "$SKILLS_DIR" ] && [ -f "$SKILLS_DIR/code-review/SKILL.md" ] && echo true || echo false )

# python3 drives every genesis script (anchors/backlog/analyze/calibration). Without it → degraded.
MODE=full
[ "$PY" = false ] && MODE=degraded

cat <<EOF
{
  "git": $GIT,
  "python3": $PY,
  "node": $NODE,
  "design_creator_installed": $DC,
  "code_review_installed": $CR,
  "mode": "$MODE",
  "hints": {
    "python3": "required — anchors/backlog/analyze_spec/calibration all run on python3",
    "design_creator": "if false, the design handoff is skipped — say so once, do not block",
    "code_review": "if false, the audit gate is skipped — say so once, do not block",
    "git": "if false, project-map freshness falls back to the file-hash tree stamp (still works)"
  }
}
EOF
