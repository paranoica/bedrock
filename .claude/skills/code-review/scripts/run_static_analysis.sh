#!/usr/bin/env bash
# Run available static-analysis tools and emit consolidated JSON to stdout.
#
# Usage:
#   run_static_analysis.sh [target_path] [files_list]
#     target_path  project root or subdir (default: .)
#     files_list   optional file with newline-separated paths to restrict the
#                  scan to (diff-scoped review). When given, tools only look at
#                  those paths, so findings line up with changed files.
#
# Tools probed: semgrep, gitleaks, bandit, eslint. Skipped (not failed) if absent.
# semgrep results are cached on a hash of the file inventory; an unchanged tree
# re-uses the previous run instead of re-scanning.

set -uo pipefail

TARGET="${1:-.}"
FILES_LIST="${2:-}"
CACHE_DIR="${CLAUDE_CACHE_DIR:-.claude/cache}"
mkdir -p "$CACHE_DIR"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

declare -A AVAILABLE
declare -A SKIPPED
have() { command -v "$1" >/dev/null 2>&1; }

# Resolve the set of paths to scan.
SCAN_PATHS=("$TARGET")
if [ -n "$FILES_LIST" ] && [ -f "$FILES_LIST" ]; then
  mapfile -t SCAN_PATHS < <(grep -v '^[[:space:]]*$' "$FILES_LIST")
  [ "${#SCAN_PATHS[@]}" -eq 0 ] && SCAN_PATHS=("$TARGET")
fi

# Inventory hash for caching: tool inputs that affect output.
inventory_hash() {
  { printf '%s\n' "$@"
    find "${SCAN_PATHS[@]}" -type f \
      \( -name '*.py' -o -name '*.js' -o -name '*.jsx' -o -name '*.ts' \
         -o -name '*.tsx' -o -name '*.go' -o -name '*.rb' -o -name '*.php' \) \
      -printf '%p %s %T@\n' 2>/dev/null | sort
  } | sha256sum | cut -d' ' -f1
}

# -------- semgrep (cached) --------
SEMGREP_CONFIGS=(p/security-audit p/owasp-top-ten p/javascript p/python p/secrets)
if have semgrep; then
  AVAILABLE[semgrep]=1
  SG_VER="$(semgrep --version 2>/dev/null | head -1)"
  KEY="$(inventory_hash "semgrep" "$SG_VER" "${SEMGREP_CONFIGS[@]}")"
  CACHE_FILE="$CACHE_DIR/semgrep-$KEY.json"
  if [ -s "$CACHE_FILE" ]; then
    cp "$CACHE_FILE" "$TMPDIR/semgrep.json"
    AVAILABLE[semgrep]="cached"
  else
    cfg=(); for c in "${SEMGREP_CONFIGS[@]}"; do cfg+=(--config "$c"); done
    # No --error flag: semgrep exits 0 on findings by default, so a clean exit
    # does not mean "no findings". (The old --error-on-findings flag was invalid
    # and aborted the whole run.)
    semgrep "${cfg[@]}" --json --quiet --metrics=off --timeout 60 \
            "${SCAN_PATHS[@]}" > "$TMPDIR/semgrep.json" 2>"$TMPDIR/semgrep.err" || true
    if [ -s "$TMPDIR/semgrep.json" ] && python3 -c 'import json,sys;json.load(open(sys.argv[1]))' "$TMPDIR/semgrep.json" 2>/dev/null; then
      cp "$TMPDIR/semgrep.json" "$CACHE_FILE"
    else
      printf '{"results":[],"errors":["semgrep produced no valid output: %s"]}' \
        "$(tr -d '"' < "$TMPDIR/semgrep.err" | head -c 200)" > "$TMPDIR/semgrep.json"
    fi
  fi
else
  SKIPPED[semgrep]="not installed (pip install semgrep)"
  echo '{"results":[]}' > "$TMPDIR/semgrep.json"
fi

# -------- gitleaks (handles old `detect` and new `dir`/`git` subcommands) --------
if have gitleaks; then
  AVAILABLE[gitleaks]=1
  GL_OUT="$TMPDIR/gitleaks.json"
  if gitleaks dir --help >/dev/null 2>&1; then
    # gitleaks >= 8.19: `dir` scans files regardless of git
    gitleaks dir "$TARGET" --report-format json --report-path "$GL_OUT" \
             --no-banner --exit-code 0 >/dev/null 2>&1 || true
  else
    # older gitleaks: `detect` needs --no-git to scan a plain directory
    gitleaks detect --source "$TARGET" --no-git --report-format json \
             --report-path "$GL_OUT" --no-banner --exit-code 0 >/dev/null 2>&1 || true
  fi
  [ -s "$GL_OUT" ] || echo '[]' > "$GL_OUT"
else
  SKIPPED[gitleaks]="not installed (brew install gitleaks)"
  echo '[]' > "$TMPDIR/gitleaks.json"
fi

# -------- bandit (Python) --------
if have bandit && find "${SCAN_PATHS[@]}" -name "*.py" -print -quit 2>/dev/null | grep -q .; then
  AVAILABLE[bandit]=1
  bandit -r "${SCAN_PATHS[@]}" -f json -o "$TMPDIR/bandit.json" \
         --severity-level low --confidence-level low --quiet 2>/dev/null || true
  [ -s "$TMPDIR/bandit.json" ] || echo '{"results":[]}' > "$TMPDIR/bandit.json"
else
  have bandit || SKIPPED[bandit]="not installed (pip install bandit) — needed for Python"
  echo '{"results":[]}' > "$TMPDIR/bandit.json"
fi

# -------- eslint (JS/TS) --------
if have npx && [ -f "$TARGET/package.json" ]; then
  if find "$TARGET" -maxdepth 3 \
       \( -name ".eslintrc*" -o -name "eslint.config.*" \) -print -quit 2>/dev/null | grep -q .; then
    AVAILABLE[eslint]=1
    (cd "$TARGET" && npx --no-install eslint . --format json) \
      > "$TMPDIR/eslint.json" 2>/dev/null || true
    [ -s "$TMPDIR/eslint.json" ] || echo '[]' > "$TMPDIR/eslint.json"
  else
    SKIPPED[eslint]="no eslint config found in project"
    echo '[]' > "$TMPDIR/eslint.json"
  fi
else
  [ -f "$TARGET/package.json" ] && SKIPPED[eslint]="npx not available"
  echo '[]' > "$TMPDIR/eslint.json"
fi

# -------- consolidate --------
emit_empty_if_bad() { python3 -c 'import json,sys;json.load(open(sys.argv[1]))' "$1" 2>/dev/null || echo "$2" > "$1"; }
emit_empty_if_bad "$TMPDIR/semgrep.json" '{"results":[]}'
emit_empty_if_bad "$TMPDIR/gitleaks.json" '[]'
emit_empty_if_bad "$TMPDIR/bandit.json" '{"results":[]}'
emit_empty_if_bad "$TMPDIR/eslint.json" '[]'

if have jq; then
  jq -n \
    --slurpfile semgrep "$TMPDIR/semgrep.json" \
    --slurpfile gitleaks "$TMPDIR/gitleaks.json" \
    --slurpfile bandit "$TMPDIR/bandit.json" \
    --slurpfile eslint "$TMPDIR/eslint.json" \
    --arg available "$(printf '%s\n' "${!AVAILABLE[@]}" | paste -sd ',' -)" \
    --arg skipped "$(for k in "${!SKIPPED[@]}"; do echo "$k:${SKIPPED[$k]}"; done | paste -sd ';' -)" \
    '{
       tools_available: ($available | split(",") | map(select(length > 0))),
       tools_skipped: ($skipped | split(";") | map(select(length > 0))),
       semgrep: ($semgrep[0] // {results: []}),
       gitleaks: ($gitleaks[0] // []),
       bandit: ($bandit[0] // {results: []}),
       eslint: ($eslint[0] // [])
     }'
else
  echo '{"error":"jq not installed; cannot consolidate. Install jq or read tool outputs on stderr."}'
  for t in semgrep gitleaks bandit eslint; do
    echo "=== $t ===" >&2; cat "$TMPDIR/$t.json" >&2
  done
fi
