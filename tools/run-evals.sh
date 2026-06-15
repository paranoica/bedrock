#!/usr/bin/env bash
# Template self-test — the WHOLE system as one blocking gate. Runs every regression and exits
# non-zero if ANY fails (AND, not "ran and looked"). This is the single command CI runs and the one
# a contributor runs locally:   bash tools/run-evals.sh
#
# Note: no `set -e` on purpose — we run every check and report all failures, then fail if any did.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
step() { printf '\n── %s ──\n' "$1"; }

step "drift-check (canon ↔ project-map CONTRACT ↔ genesis)"
python3 "$ROOT/tools/drift-check.py" || fail=1

step "genesis seam regression (anchor/normalizer + gate teeth)"
python3 "$ROOT/.claude/skills/genesis/evals/seam_test.py" || fail=1

step "genesis parametricity (non-web fixture: a backup CLI)"
python3 "$ROOT/.claude/skills/genesis/evals/parametric_test.py" || fail=1

step "project-map smoke (build, then --check must be fresh)"
if python3 "$ROOT/tools/project-map/build.py" "$ROOT" >/dev/null \
   && python3 "$ROOT/tools/project-map/build.py" "$ROOT" --check >/dev/null; then
  echo "  ok"
else
  echo "  FAIL"; fail=1
fi

step "codex skill-mirror drift (.agents/skills vs .claude/skills)"
python3 "$ROOT/tools/port-skills.py" --check --root "$ROOT" || fail=1

step "design-creator contrast floor (selftest — zero-dep)"
if command -v node >/dev/null 2>&1; then
  node "$ROOT/.claude/skills/design-creator/tools/contrast.mjs" selftest || fail=1
else
  echo "  skip: node not available"
fi

step "design-creator motion gate (render-backed; self-skips without a browser)"
if command -v node >/dev/null 2>&1; then
  node "$ROOT/.claude/skills/design-creator/evals/motion.mjs" || fail=1
else
  echo "  skip: node not available"
fi

if [ "$fail" -ne 0 ]; then
  printf '\nEVALS: FAIL\n'; exit 1
fi
printf '\nEVALS: PASS\n'
