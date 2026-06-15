#!/usr/bin/env bash
# Wrapper that calls check_cves.py with the right python.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-.}"

if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/check_cves.py" "$TARGET"
elif command -v python >/dev/null 2>&1; then
  python "$SCRIPT_DIR/check_cves.py" "$TARGET"
else
  echo '{"error":"python not installed; cannot run CVE check"}'
  exit 1
fi
