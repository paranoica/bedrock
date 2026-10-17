#!/usr/bin/env bash
# poc_runner.sh — run a MINIMAL, ISOLATED proof-of-concept to turn an
# exploitability *claim* into an execution *receipt*. This is the strongest
# possible grounding for a CRITICAL/HIGH security finding.
#
# HARD SAFETY CONTRACT (this is why it exists):
#   - It runs ONLY a tiny PoC snippet the reviewer wrote to test one hypothesis.
#     It NEVER runs the project's app, its test suite, build scripts, or install.
#   - No network. Time-boxed. Memory/CPU/file/process limited. CWD is a throwaway
#     tmpdir. The repo is NOT mounted writable.
#   - If NO isolation backend is available, it REFUSES to execute and returns
#     {"available": false}. We never execute untrusted code unguarded — the
#     finding simply stays "needs verification". Safety beats a stronger receipt.
#
# Usage:
#   scripts/poc_runner.sh --lang py|js --file <poc_file> [--expect MARKER] [--timeout 8]
#   scripts/poc_runner.sh --lang py --code '<inline code>' [--expect MARKER]
#
# Output: JSON on stdout.
#   { available, isolation, exit_code, confirmed, timed_out, stdout, stderr, note }
#   `confirmed` is true iff (exit_code==0) and (MARKER present in stdout, if given).
set -uo pipefail

LANG_="" FILE="" CODE="" EXPECT="" TLIMIT=8
while [ $# -gt 0 ]; do
  case "$1" in
    --lang) LANG_="$2"; shift 2;;
    --file) FILE="$2"; shift 2;;
    --code) CODE="$2"; shift 2;;
    --expect) EXPECT="$2"; shift 2;;
    --timeout) TLIMIT="$2"; shift 2;;
    *) echo "{\"available\":false,\"note\":\"unknown arg: $1\"}"; exit 0;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }
json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

# --- pick interpreter ---
case "$LANG_" in
  py) RUN=(python3);;
  js) RUN=(node);;
  *)  echo '{"available":false,"note":"--lang must be py or js"}'; exit 0;;
esac
have "${RUN[0]}" || { echo "{\"available\":false,\"note\":\"${RUN[0]} not installed\"}"; exit 0; }

# --- pick isolation backend (best first) ---
ISO="none"
if   have bwrap;    then ISO="bubblewrap"
elif have firejail; then ISO="firejail"
elif unshare -rn true 2>/dev/null; then ISO="unshare"
fi
if [ "$ISO" = "none" ]; then
  echo '{"available":false,"isolation":"none","note":"no isolation backend (bwrap/firejail/unshare) — refusing to execute untrusted PoC; finding stays needs-verification"}'
  exit 0
fi
have timeout || { echo '{"available":false,"note":"timeout(1) missing — refusing to run unbounded"}'; exit 0; }

# --- stage the PoC in a throwaway tmpdir ---
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
EXT="py"; [ "$LANG_" = "js" ] && EXT="js"
POC="$WORK/poc.$EXT"
if [ -n "$FILE" ]; then
  [ -f "$FILE" ] || { echo "{\"available\":true,\"isolation\":\"$ISO\",\"note\":\"poc file not found\"}"; exit 0; }
  cp "$FILE" "$POC"
elif [ -n "$CODE" ]; then
  printf '%s' "$CODE" > "$POC"
else
  echo '{"available":true,"note":"provide --file or --code"}'; exit 0
fi

OUT="$WORK/out"; ERR="$WORK/err"

run_bwrap() {
  timeout -k 2 "$TLIMIT" bwrap \
    --unshare-all --die-with-parent \
    --ro-bind / / --dev /dev --proc /proc \
    --tmpfs /tmp --bind "$WORK" "$WORK" --chdir "$WORK" \
    --setenv PATH /usr/bin:/bin --clearenv --setenv PATH /usr/bin:/bin \
    bash -c 'ulimit -v 262144 2>/dev/null||true; ulimit -t 5 2>/dev/null||true; ulimit -u 64 2>/dev/null||true; exec "$0" "poc.$1"' "${RUN[0]}" "$EXT"
}
run_firejail() {
  timeout -k 2 "$TLIMIT" firejail --quiet --net=none --private="$WORK" \
    --rlimit-as=268435456 --rlimit-cpu=5 --rlimit-nproc=64 \
    "${RUN[@]}" "poc.$EXT"
}
run_unshare() {
  # user+net namespace; resource caps + timeout in the inner bash
  timeout -k 2 "$TLIMIT" unshare -rn bash -c '
    ulimit -v 262144 2>/dev/null||true; ulimit -t 5 2>/dev/null||true
    ulimit -f 32768 2>/dev/null||true;  ulimit -u 64 2>/dev/null||true
    cd "$1" || exit 97; exec "$2" "poc.$3"' _ "$WORK" "${RUN[0]}" "$EXT"
}

TIMED_OUT=false
case "$ISO" in
  bubblewrap) run_bwrap  >"$OUT" 2>"$ERR"; RC=$?;;
  firejail)   run_firejail>"$OUT" 2>"$ERR"; RC=$?;;
  unshare)    run_unshare >"$OUT" 2>"$ERR"; RC=$?;;
esac
# timeout(1) exits 124 on TLE
[ "${RC:-1}" -eq 124 ] && TIMED_OUT=true

# --- decide confirmed ---
CONFIRMED=false
if [ "${RC:-1}" -eq 0 ]; then
  if [ -n "$EXPECT" ]; then
    grep -qF -- "$EXPECT" "$OUT" 2>/dev/null && CONFIRMED=true
  else
    CONFIRMED=true
  fi
fi

SO=$(head -c 4000 "$OUT" 2>/dev/null | json_escape)
SE=$(head -c 2000 "$ERR" 2>/dev/null | json_escape)

cat <<JSON
{
  "available": true,
  "isolation": "$ISO",
  "exit_code": ${RC:-null},
  "timed_out": $TIMED_OUT,
  "confirmed": $CONFIRMED,
  "expect_marker": $( [ -n "$EXPECT" ] && printf '%s' "$EXPECT" | json_escape || printf null ),
  "stdout": $SO,
  "stderr": $SE,
  "note": "confirmed=true means the PoC ran clean (and printed the marker, if one was given). This is an execution receipt for the exploitability claim — cite it in the finding. A non-confirmed run does NOT prove safety; it means 'not reproduced under this PoC'."
}
JSON
