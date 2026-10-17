#!/bin/sh
# Run the bench evals. Their cases and graders hold the answers, so they live with the answer
# key outside this repository and are copied into the plugin only for the run.
set -eu
KEY="${BEDROCK_BENCH_KEY:-$HOME/.local/share/bedrock-bench-key}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$HERE/plugins/bedrock/evals-bench"
[ -d "$KEY/evals" ] || { echo "no bench evals in $KEY/evals" >&2; exit 2; }
rm -rf "$TARGET"
cp -r "$KEY/evals" "$TARGET"
trap 'rm -rf "$TARGET"' EXIT INT TERM
# Results go outside the copy, or the cleanup would delete them.
OUT="$HERE/bench/results/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
claude plugin eval "$HERE/plugins/bedrock" --eval-dir evals-bench --scaffold --no-publish \
  --output-dir "$OUT" --report "$OUT/report.html" "$@"
echo "results: $OUT"
