#!/usr/bin/env bash
# Deterministic regressions for the code-review skill. No model calls.
# Guards the bugs v1 shipped: silent lockfile-parser misses and ungrounded
# (hallucinated) findings slipping through.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../scripts"
fail=0
pass() { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fail=1; }

echo "== 1. lockfile parser coverage (regression: v1 returned [] for these) =="
if python3 - "$SCRIPTS/check_cves.py" "$HERE/fixtures/lockfiles" <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("c", sys.argv[1])
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
d = Path(sys.argv[2])
pnpm = c.parse_pnpm_lock(d / "pnpm-lock.yaml")
yarn = c.parse_yarn_lock(d / "yarn.lock")
ok = any(n == "lodash" for _, n, _ in pnpm) and any(n == "axios" for _, n, _ in yarn)
sys.exit(0 if ok else 1)
PY
then
  pass "pnpm v9 + yarn berry parse to non-empty"
else
  bad "modern lockfiles parsed empty"
fi

echo "== 2. verifier cuts hallucinated findings =="
python3 "$SCRIPTS/verify_findings.py" "$HERE/fixtures/hallucinated_findings.json" \
        "$HERE" "$HERE/fixtures/osv_empty.json" >/tmp/vh.json || true
cuts=$(python3 -c 'import json;s=json.load(open("/tmp/vh.json"))["summary"];print(sum(s.get(k,0) for k in ("CUT_NO_FILE","CUT_NO_QUOTE","CUT_BAD_CVE")))')
if [ "$cuts" = "3" ]; then
  pass "all 3 hallucinations cut"
else
  bad "expected 3 cuts, got $cuts"
fi

echo "== 3. verifier keeps a real finding (no over-cutting) =="
python3 "$SCRIPTS/verify_findings.py" "$HERE/fixtures/real_findings.json" "$HERE" >/tmp/vr.json || true
kept=$(python3 -c 'import json;s=json.load(open("/tmp/vr.json"))["summary"];print(s.get("VERIFIED",0)+s.get("RELOCATE",0))')
if [ "$kept" = "1" ]; then
  pass "real finding kept (verified/relocated)"
else
  bad "real finding wrongly cut"
fi

echo "== 4. change_risk flags mixed concerns + risky-no-tests =="
python3 "$SCRIPTS/change_risk.py" --files "$HERE/fixtures/changes_risky.json" "$HERE" >/tmp/cr.json || true
flags=$(python3 -c 'import json;print(",".join(sorted(f["flag"] for f in json.load(open("/tmp/cr.json"))["flags"])))')
if echo "$flags" | grep -q "mixed_concerns" && echo "$flags" | grep -q "risky_no_tests"; then
  pass "change_risk flags: $flags"
else
  bad "expected mixed_concerns+risky_no_tests, got: $flags"
fi

echo "== 5. calibration brier score computes =="
export CLAUDE_CACHE_DIR=/tmp/eval_cal; rm -rf /tmp/eval_cal
# shellcheck disable=SC2086  # intentional split: each pair is "<p> <outcome>"
for pair in "0.9 1" "0.9 1" "0.65 0" "0.35 0"; do python3 "$SCRIPTS/calibration.py" record $pair >/dev/null; done
brier=$(python3 "$SCRIPTS/calibration.py" report | python3 -c 'import json,sys;print(json.load(sys.stdin)["brier_score"])')
unset CLAUDE_CACHE_DIR
if python3 -c "import sys;sys.exit(0 if 0.0<=$brier<=1.0 else 1)"; then
  pass "brier score computed: $brier"
else
  bad "brier score invalid: $brier"
fi

echo "== 5b. CVSS 4.0 severity is handled (v4 vector scored/fallback, never silent UNKNOWN) =="
if python3 - "$SCRIPTS/check_cves.py" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("c", sys.argv[1])
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
# v4-only vector + GHSA text, with the osv.dev#2335 integer-type quirk -> text band, not UNKNOWN
b1,_,_ = c.assess_severity({"severity":[{"type":3,"score":"CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"}],"database_specific":{"severity":"HIGH"}})
# v4-only, no text, no cvss lib -> REVIEW (flagged for manual scoring), never UNKNOWN/clean
b2,_,vec = c.assess_severity({"severity":[{"type":"CVSS_V4","score":"CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N"}]})
sys.exit(0 if (b1=="HIGH" and b2=="REVIEW" and vec) else 1)
PY
then
  pass "v4 vector -> text fallback / REVIEW, never silent UNKNOWN"
else
  bad "CVSS 4.0 advisory mishandled (silent UNKNOWN or dropped vector)"
fi

echo "== 7. labeled corpus: golden candidate scores recall=1.0, 0 FP, 0 halluc =="
python3 "$HERE/score.py" "$HERE/fixtures/golden_candidate.json" "$HERE/expected.json" "$HERE" >/tmp/sc.json 2>&1 || true
if python3 -c 'import json;r=json.load(open("/tmp/sc.json"));import sys;sys.exit(0 if (r["recall"]==1.0 and r["false_positives"]==0 and r["hallucinations"]==0) else 1)' 2>/dev/null; then
  pass "golden candidate: recall 1.0 / precision $(python3 -c "import json;print(json.load(open('/tmp/sc.json'))['precision'])") / F1 $(python3 -c "import json;print(json.load(open('/tmp/sc.json'))['f1'])")"
else
  cat /tmp/sc.json; bad "corpus scoring regressed (fixture/label/golden drift)"
fi

echo
echo "== 8. report linter: passes a compliant report, fails a gate-skipped one =="
RGOOD=/tmp/_rep_good.md; RBAD=/tmp/_rep_bad.md
cat > "$RGOOD" <<'MD'
# Code Review — x
**Scope:** 2 files
**Stack detected:** Python 3.12
**Tools run:** semgrep, OSV.dev
**Verification:** tier B · `verify_findings.py`: VERIFIED=2 RELOCATE=0 CUT=1 NEEDS_HUMAN=0 · receipt:0123456789ab
## Coverage & limits
Read both files. Grounds what it found, cannot certify what it didn't.
## Verdict
Fix the CRITICAL.
MD
grep -v '^\*\*Verification:\*\*' "$RGOOD" > "$RBAD"   # drop the grounding receipt
if python3 "$SCRIPTS/check_report.py" "$RGOOD" >/dev/null 2>&1 \
   && ! python3 "$SCRIPTS/check_report.py" "$RBAD" >/dev/null 2>&1; then
  pass "linter accepts compliant report, rejects missing Verification receipt"
else
  bad "report linter mis-graded (compliant rejected or skipped-gate accepted)"
fi

echo
echo "== 9. verifier grounds a real finding on its TRUE line when a short quote repeats =="
RDIR=/tmp/_loc; mkdir -p "$RDIR/app"
printf 'def a():\n    run(x)        # benign, shares token\ndef b(req):\n    run(req.input) # the real sink\n' > "$RDIR/app/m.py"
printf '{"findings":[{"id":"L","severity":"HIGH","file":"app/m.py","lines":[4,4],"quote":"run(","cve":null}]}' > "$RDIR/f.json"
v=$(python3 "$SCRIPTS/verify_findings.py" "$RDIR/f.json" "$RDIR" 2>/dev/null \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["results"][0]["verdict"])')
if [ "$v" = "VERIFIED" ]; then
  pass "short repeated quote stays VERIFIED at claimed line (not relocated onto benign line)"
else
  bad "locate regressed: got $v, expected VERIFIED (first-match bug back?)"
fi

echo
echo "== 10. receipt binding: forged Verification line is rejected, honest one passes =="
# Build a tiny real repo + finding, run the verifier (writes a hash-bound receipt),
# then prove check_report --receipt accepts the honest report and rejects three forgeries:
# (a) wrong count, (b) wrong receipt id, (c) a source file mutated after verification.
BIND=$(mktemp -d)
mkdir -p "$BIND/repo"
printf 'def q(u):\n    cursor.execute("SELECT * FROM t WHERE id=%%s" %% u)\n' > "$BIND/repo/app.py"
cat > "$BIND/findings.json" <<JSON
{"findings":[{"id":"F1","severity":"HIGH","category":"sqli","confidence":"high","file":"app.py","lines":[2,2],"quote":"cursor.execute(\"SELECT * FROM t WHERE id=%s\" % u)","cve":null}]}
JSON
python3 "$SCRIPTS/verify_findings.py" "$BIND/findings.json" "$BIND/repo" >/dev/null 2>&1 || true
RID=$(python3 -c "import json;print(json.load(open('$BIND/repo/.review/verify-receipt.json'))['receipt_id'])")
mkreport () {  # $1=counts-VERIFIED $2=receiptid -> stdout a full report
cat <<MD
# Code Review — bind
**Scope:** 1 file
**Stack detected:** Python 3.12
**Tools run:** none (offline)
**Verification:** tier B · \`verify_findings.py\`: VERIFIED=$1 RELOCATE=0 CUT=0 NEEDS_HUMAN=0 · receipt:$2
## Coverage & limits
Read app.py. Grounds what it found.
## Verdict
Fix the HIGH.
MD
}
HONEST=$(mktemp); FORGE_CNT=$(mktemp); FORGE_ID=$(mktemp)
mkreport 1 "$RID" > "$HONEST"
mkreport 9 "$RID" > "$FORGE_CNT"           # lied about the count
mkreport 1 "ffffffffffff" > "$FORGE_ID"    # invented a receipt id
RC="$SCRIPTS/check_report.py"; R="$BIND/repo/.review/verify-receipt.json"
ok1=1; python3 "$RC" "$HONEST"    --receipt "$R" --repo "$BIND/repo" >/dev/null 2>&1 || ok1=0
ok2=1; python3 "$RC" "$FORGE_CNT" --receipt "$R" --repo "$BIND/repo" >/dev/null 2>&1 || ok2=0
ok3=1; python3 "$RC" "$FORGE_ID"  --receipt "$R" --repo "$BIND/repo" >/dev/null 2>&1 || ok3=0
# now mutate the source after verification: honest report must FAIL (stale receipt)
printf '\n# touched after the receipt\n' >> "$BIND/repo/app.py"
ok4=1; python3 "$RC" "$HONEST" --receipt "$R" --repo "$BIND/repo" >/dev/null 2>&1 || ok4=0
if [ "$ok1" = 1 ] && [ "$ok2" = 0 ] && [ "$ok3" = 0 ] && [ "$ok4" = 0 ]; then
  pass "honest report binds; forged counts, forged id, and post-hoc file edits are all rejected"
else
  bad "receipt binding mis-graded (honest=$ok1 want1; forge_count=$ok2 want0; forge_id=$ok3 want0; stale=$ok4 want0)"
fi
rm -rf "$BIND" "$HONEST" "$FORGE_CNT" "$FORGE_ID"

echo
echo "== 6. structural regressions (v2 refactor: SKILL size, router paths, spine, build_index langs) =="
if python3 "$HERE/check_structure.py" > /tmp/_struct_out 2>&1; then
  pass "structural checks passed"
else
  cat /tmp/_struct_out
  bad "structural checks failed"
fi

echo
if [ $fail -eq 0 ]; then
  echo "ALL REGRESSIONS PASSED"
else
  echo "SOME REGRESSIONS FAILED"
fi
exit $fail
