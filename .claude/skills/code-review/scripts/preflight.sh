#!/usr/bin/env bash
# preflight.sh — probe the environment ONCE at the start of a review and emit a
# capability report as JSON. SKILL.md (Step 0) reads this and announces the
# operating mode to the user instead of discovering missing pieces mid-review.
#
# Usage: scripts/preflight.sh [--no-net]
#   --no-net   skip the network probe (offline / sandboxed runs)
#
# Output: JSON on stdout. Never fails the run — a missing tool is data, not an error.
set -uo pipefail

NET=1
[ "${1:-}" = "--no-net" ] && NET=0

have() { command -v "$1" >/dev/null 2>&1; }
b() { if [ "$1" -eq 0 ]; then echo true; else echo false; fi; }

# --- static-analysis toolchain ---
have semgrep;  HAS_SEMGREP=$?
have gitleaks; HAS_GITLEAKS=$?
have bandit;   HAS_BANDIT=$?
have eslint;   HAS_ESLINT=$?
have python3;  HAS_PY=$?
have node;     HAS_NODE=$?

# --- PoC-execution isolation backends (for Step 5d, execution-grounded verify) ---
# Ordered best→worst. The first available is what poc_runner.sh will use.
ISO="none"
if   have bwrap;    then ISO="bubblewrap"
elif have firejail; then ISO="firejail"
elif have nsjail;   then ISO="nsjail"
elif unshare -rn true 2>/dev/null; then ISO="unshare"   # user+net namespaces work
fi
# timeout + a way to drop network is the minimum for a *guarded* run
have timeout; HAS_TIMEOUT=$?

# --- OSV reachability (CVE layer) ---
OSV_REACHABLE=1
OSV_DETAIL="not probed (--no-net)"
if [ "$NET" -eq 1 ]; then
  if have curl; then
    CODE=$(curl -s -m 5 -o /dev/null -w '%{http_code}' \
      -X POST https://api.osv.dev/v1/query \
      -H 'Content-Type: application/json' \
      -d '{"package":{"name":"lodash","ecosystem":"npm"},"version":"4.17.20"}' 2>/dev/null || echo 000)
    if [ "$CODE" = "200" ]; then OSV_REACHABLE=0; OSV_DETAIL="api.osv.dev reachable (HTTP 200)";
    else OSV_REACHABLE=1; OSV_DETAIL="api.osv.dev unreachable (HTTP ${CODE}) — likely allowlist/egress block"; fi
  else
    OSV_REACHABLE=1; OSV_DETAIL="curl not installed — cannot probe OSV"
  fi
fi

# --- install hints for whatever is missing ---
HINTS=""
[ "$HAS_SEMGREP"  -ne 0 ] && HINTS="${HINTS}semgrep: pipx install semgrep; "
[ "$HAS_GITLEAKS" -ne 0 ] && HINTS="${HINTS}gitleaks: brew install gitleaks (or download release); "
[ "$HAS_BANDIT"   -ne 0 ] && HINTS="${HINTS}bandit: pipx install bandit; "
[ "$HAS_ESLINT"   -ne 0 ] && HINTS="${HINTS}eslint: npx eslint (needs project config); "
[ "$ISO" = "none" ]       && HINTS="${HINTS}poc-isolation: install bubblewrap/firejail (else PoC execution is disabled, findings stay needs-verification); "
[ "$OSV_REACHABLE" -ne 0 ] && [ "$NET" -eq 1 ] && HINTS="${HINTS}OSV: allow api.osv.dev in network settings, or rely on web-search fallback; "
[ -z "$HINTS" ] && HINTS="none — full toolchain available"

# --- can we run PoCs at all? ---
# Require an isolation backend AND timeout. Without isolation we DO NOT execute
# untrusted PoCs — execution-grounding is simply skipped (findings stay
# needs-verification). Safety first.
POC_OK=1
{ [ "$ISO" != "none" ] && [ "$HAS_TIMEOUT" -eq 0 ]; } && POC_OK=0

# --- derive the operating mode ---
MODE="degraded"
if { [ "$HAS_SEMGREP" -eq 0 ] || [ "$HAS_BANDIT" -eq 0 ] || [ "$HAS_GITLEAKS" -eq 0 ]; } && [ "$OSV_REACHABLE" -eq 0 ]; then
  MODE="full"
fi

cat <<JSON
{
  "mode": "${MODE}",
  "tools": {
    "semgrep": $(b $HAS_SEMGREP),
    "gitleaks": $(b $HAS_GITLEAKS),
    "bandit": $(b $HAS_BANDIT),
    "eslint": $(b $HAS_ESLINT),
    "python3": $(b $HAS_PY),
    "node": $(b $HAS_NODE)
  },
  "poc_execution": {
    "available": $(b $POC_OK),
    "isolation": "${ISO}",
    "timeout": $(b $HAS_TIMEOUT)
  },
  "network": {
    "osv_reachable": $(b $OSV_REACHABLE),
    "osv_detail": "${OSV_DETAIL}"
  },
  "install_hints": "${HINTS}",
  "note": "degraded mode is valid: LLM review + deterministic verify_findings.py + self-consistency still run. Missing static tools widen blind spots; OSV-unreachable means dependency CVE scan is SKIPPED (not 'no vulns') and web-search fallback carries lower confidence. If poc_execution.available is false, exploitability is asserted, not executed — affected findings stay needs-verification, never auto-promoted to CRITICAL on execution they couldn't run."
}
JSON
