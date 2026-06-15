#!/usr/bin/env python3
"""
Structural regressions for the v2 refactor. No model calls. Guards:
  - SKILL.md stays <= 500 lines and description <= 1024 chars (Anthropic skill limits)
  - index.json is valid JSON and every file path it references actually exists
  - the taint-spine, the thin-module contract, and the invariants/discipline refs exist
  - build_index.py recognizes the expanded language set (regression: was py/js only)
Exit non-zero on any failure so run_evals.sh / CI can gate.
"""
import json, os, re, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the skill dir
fails = []

def ok(m): print(f"PASS: {m}")
def bad(m): print(f"FAIL: {m}"); fails.append(m)

# 1. SKILL.md limits
skill = open(os.path.join(ROOT, "SKILL.md")).read()
n_lines = len(skill.splitlines())
if n_lines <= 500: ok(f"SKILL.md {n_lines} lines (<=500)")
else: bad(f"SKILL.md {n_lines} lines (>500, over Anthropic limit)")

m = re.search(r"^description: (.*)$", skill, re.M)
desc_len = len(m.group(1)) if m else 9999
if desc_len <= 1024: ok(f"description {desc_len} chars (<=1024)")
else: bad(f"description {desc_len} chars (>1024)")

# 2. index.json valid + every referenced file path exists
idx_path = os.path.join(ROOT, "index.json")
try:
    idx = json.load(open(idx_path))
    ok("index.json parses")
except Exception as e:
    bad(f"index.json invalid: {e}"); idx = {}

EXT = (".md", ".json", ".sh", ".py")
referenced = set()
def walk(o):
    if isinstance(o, dict):
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
    elif isinstance(o, str):
        # take the leading path token (strip trailing prose like "(COMMITTED)")
        tok = o.split(" ")[0].split("(")[0].strip()
        if tok.endswith(EXT) and "/" in tok or tok.endswith(EXT):
            referenced.add(tok)
walk(idx)
missing = [p for p in sorted(referenced)
           if p.endswith(EXT) and not p.startswith(".review")
           and not os.path.exists(os.path.join(ROOT, p))]
if not missing: ok(f"all {len(referenced)} index.json file refs resolve")
else: bad("index.json references missing files: " + ", ".join(missing))

# 3. core v2 files present
for rel in ["checklists/taint-spine.md", "checklists/lang/CONTRACT.md",
            "references/invariants.md", "references/review-discipline.md"]:
    if os.path.exists(os.path.join(ROOT, rel)): ok(f"present: {rel}")
    else: bad(f"missing core file: {rel}")

# 4. build_index.py recognizes the expanded language set
spec = importlib.util.spec_from_file_location("bi", os.path.join(ROOT, "scripts", "build_index.py"))
bi = importlib.util.module_from_spec(spec); spec.loader.exec_module(bi)
expected = {".go": "go", ".c": "c", ".cpp": "c", ".cs": "cs", ".java": "jvm",
            ".kt": "jvm", ".php": "php", ".rs": "rust", ".rb": "ruby", ".py": "py", ".ts": "js"}
wrong = {e: bi.lang_of("x" + e) for e, want in expected.items() if bi.lang_of("x" + e) != want}
if not wrong: ok(f"build_index recognizes {len(expected)} extensions")
else: bad(f"build_index lang_of wrong for: {wrong}")

# smoke: the new parsers run and find a def
go_defs, _, _ = bi.parse_go("func Foo(x int) int { return x }")
c_defs, _, _ = bi.parse_cfamily("int bar(char *p) { return baz(p); }", "c")
if "Foo" in go_defs and "bar" in c_defs: ok("go/c parsers extract defs")
else: bad(f"parser smoke failed: go={go_defs} c={c_defs}")

print()
if fails:
    print(f"STRUCTURAL REGRESSIONS FAILED ({len(fails)})")
    sys.exit(1)
print("ALL STRUCTURAL CHECKS PASSED")
