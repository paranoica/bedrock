#!/usr/bin/env python3
"""
build_index.py — a lightweight, persistent, repo-local code map so cross-module
reasoning is not re-derived from scratch (and not token-bounded to whatever was
skimmed) on every review.

This is NOT a full semantic graph. It is the cheap 80%: for every source file it
records the symbols it DEFINES (functions/classes/methods) and the names it CALLS.
From that you can answer the two questions diff-only review is blind to:
  - "who calls this function I'm about to change?"  (reverse edges)
  - "where is this symbol defined?"                 (forward edges)
which is exactly what catches the cross-cutting-change bugs (a removed guard, a
changed contract, a now-reachable sink) that a single-file pass misses.

Design:
  - stdlib only. Python via `ast` (accurate). Go, C/C++, C#, Java/Kotlin, PHP,
    Rust, Ruby, JS/TS via regex (good-enough defs+calls, not a full parse).
  - Incremental: each file's content hash is stored; unchanged files are reused.
  - Output: .review/index.json  {version, files:{path:{hash,defs,calls,lang}},
            symbols:{name:[paths]}, callers:{name:[paths]}}
  - Read-only on the repo. Writes only under .review/.

Usage:
  scripts/build_index.py <repo_root> [--out .review/index.json]
  # then query:
  scripts/build_index.py <repo_root> --callers <symbol>
  scripts/build_index.py <repo_root> --defs <symbol>

Exit 0 always (a parse error on one file is recorded, not fatal).
"""
import sys, os, json, ast, re, hashlib, argparse

PY_EXT = {".py"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
GO_EXT = {".go"}
C_EXT = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
CS_EXT = {".cs"}
JVM_EXT = {".java", ".kt", ".kts"}
PHP_EXT = {".php"}
RUST_EXT = {".rs"}
RUBY_EXT = {".rb"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".next", ".review", "vendor", ".mypy_cache", ".pytest_cache", "target",
             "bin", "obj", ".gradle"}
INDEX_VERSION = 2

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def parse_python(src):
    defs, calls = set(), set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return defs, calls, "py-parse-error"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs.add(node.name)
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                calls.add(f.attr)
    return defs, calls, "py"

# JS/TS: regex-level. Catches function decls, methods, arrow assignments, and calls.
JS_DEF = re.compile(
    r"(?:function\s+([A-Za-z_$][\w$]*))"
    r"|(?:class\s+([A-Za-z_$][\w$]*))"
    r"|(?:(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)"
    r"|(?:^\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{)",  # bare method shorthand
    re.M)
JS_CALL = re.compile(r"(?:\.|\b)([A-Za-z_$][\w$]*)\s*\(")
JS_KW = {"if","for","while","switch","catch","return","function","typeof","await",
         "super","this","constructor"}

def parse_js(src):
    defs, calls = set(), set()
    for m in JS_DEF.finditer(src):
        for g in m.groups():
            if g:
                defs.add(g)
    for m in JS_CALL.finditer(src):
        name = m.group(1)
        if name not in JS_KW:
            calls.add(name)
    return defs, calls, "js"

# --- Regex-level parsers for brace/keyword languages (good-enough, like JS). ---
# Shared call shape: an identifier immediately followed by "(". Per-language keyword
# sets strip control-flow so it isn't logged as a "call".
CALL_RE = re.compile(r"(?:\.|::|->|\b)([A-Za-z_]\w*)\s*\(")
COMMON_KW = {"if", "for", "while", "switch", "catch", "return", "sizeof", "typeof",
             "defer", "go", "func", "fn", "def", "function", "match", "with", "await",
             "throw", "new", "delete", "using", "lock", "synchronized", "foreach",
             "elif", "unless", "do", "case", "when"}

def _calls(src, extra_kw=frozenset()):
    out = set()
    kw = COMMON_KW | extra_kw
    for m in CALL_RE.finditer(src):
        n = m.group(1)
        if n not in kw:
            out.add(n)
    return out

GO_DEF = re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(", re.M)
def parse_go(src):
    defs = set(GO_DEF.findall(src))
    return defs, _calls(src), "go"

RUST_DEF = re.compile(r"^\s*(?:pub\s+(?:\([^)]*\)\s*)?)?(?:async\s+)?(?:unsafe\s+)?fn\s+([A-Za-z_]\w*)", re.M)
RUST_TYPE = re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)", re.M)
def parse_rust(src):
    defs = set(RUST_DEF.findall(src)) | set(RUST_TYPE.findall(src))
    return defs, _calls(src, {"impl", "let", "mut", "move"}), "rust"

PHP_DEF = re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\(|\b(?:class|trait|interface)\s+([A-Za-z_]\w*)", re.M)
def parse_php(src):
    defs = set()
    for a, b in PHP_DEF.findall(src):
        if a: defs.add(a)
        if b: defs.add(b)
    return defs, _calls(src, {"echo", "print", "array", "isset", "empty", "list"}), "php"

RUBY_DEF = re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[!?=]?)|^\s*(?:class|module)\s+([A-Za-z_]\w*)", re.M)
def parse_ruby(src):
    defs = set()
    for a, b in RUBY_DEF.findall(src):
        if a: defs.add(a)
        if b: defs.add(b)
    return defs, _calls(src, {"puts", "require", "attr_accessor", "attr_reader", "raise", "yield"}), "ruby"

# C-family / Java / C# / Kotlin: a function/method is roughly
#   [modifiers/return-type ...] Name( ... ) [throws ...] {
# Catch "Name(" that is followed (allowing args) by "{", with a type-ish token before it.
CFAM_DEF = re.compile(
    r"(?:^|[;{}\s])(?:[A-Za-z_][\w:<>,*&\[\]\s]+?\s+)([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:throws[^{;]*)?\{",
    re.M)
KOTLIN_DEF = re.compile(r"\bfun\s+(?:<[^>]*>\s*)?(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)\s*\(", re.M)
TYPE_DEF = re.compile(r"\b(?:class|struct|interface|enum|record|object)\s+([A-Za-z_]\w*)", re.M)
def parse_cfamily(src, lang, extra_kw=frozenset()):
    defs = set(m.group(1) for m in CFAM_DEF.finditer(src))
    defs |= set(KOTLIN_DEF.findall(src))   # harmless on C/Java (no `fun `)
    defs |= set(TYPE_DEF.findall(src))
    defs -= COMMON_KW
    return defs, _calls(src, extra_kw), lang


def lang_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in PY_EXT: return "py"
    if ext in JS_EXT: return "js"
    if ext in GO_EXT: return "go"
    if ext in C_EXT: return "c"
    if ext in CS_EXT: return "cs"
    if ext in JVM_EXT: return "jvm"
    if ext in PHP_EXT: return "php"
    if ext in RUST_EXT: return "rust"
    if ext in RUBY_EXT: return "ruby"
    return None

def iter_sources(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            full = os.path.join(dp, fn)
            if lang_of(full):
                yield full

def build(root, out_path):
    prev = {}
    if os.path.exists(out_path):
        try:
            old = json.load(open(out_path))
            if old.get("version") == INDEX_VERSION:
                prev = old.get("files", {})
        except Exception:
            prev = {}
    files = {}
    reused = scanned = 0
    for full in iter_sources(root):
        rel = os.path.relpath(full, root)
        try:
            h = file_hash(full)
        except OSError:
            continue
        if rel in prev and prev[rel].get("hash") == h:
            files[rel] = prev[rel]
            reused += 1
            continue
        try:
            src = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        lang = lang_of(full)
        if lang == "py":
            defs, calls, lang = parse_python(src)
        elif lang == "js":
            defs, calls, lang = parse_js(src)
        elif lang == "go":
            defs, calls, lang = parse_go(src)
        elif lang == "rust":
            defs, calls, lang = parse_rust(src)
        elif lang == "php":
            defs, calls, lang = parse_php(src)
        elif lang == "ruby":
            defs, calls, lang = parse_ruby(src)
        else:  # c / cs / jvm — C-family regex
            defs, calls, lang = parse_cfamily(src, lang)
        files[rel] = {"hash": h, "lang": lang,
                      "defs": sorted(defs), "calls": sorted(calls)}
        scanned += 1

    # reverse maps
    symbols, callers = {}, {}
    for rel, info in files.items():
        for d in info["defs"]:
            symbols.setdefault(d, []).append(rel)
        for c in info["calls"]:
            callers.setdefault(c, []).append(rel)

    index = {"version": INDEX_VERSION, "root": os.path.abspath(root),
             "files": files,
             "symbols": {k: sorted(set(v)) for k, v in symbols.items()},
             "callers": {k: sorted(set(v)) for k, v in callers.items()}}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(index, open(out_path, "w"), indent=0)
    return index, scanned, reused

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default=".review/index.json")
    ap.add_argument("--callers", metavar="SYMBOL",
                    help="print files that CALL this symbol, then exit")
    ap.add_argument("--defs", metavar="SYMBOL",
                    help="print files that DEFINE this symbol, then exit")
    a = ap.parse_args()
    out = a.out if os.path.isabs(a.out) else os.path.join(a.root, a.out)

    if a.callers or a.defs:
        if not os.path.exists(out):
            print(json.dumps({"error": "index not built; run without --callers/--defs first"}))
            return
        idx = json.load(open(out))
        if a.callers:
            print(json.dumps({"symbol": a.callers,
                              "callers": idx.get("callers", {}).get(a.callers, [])}))
        else:
            print(json.dumps({"symbol": a.defs,
                              "defs": idx.get("symbols", {}).get(a.defs, [])}))
        return

    idx, scanned, reused = build(a.root, out)
    print(json.dumps({
        "ok": True, "out": out,
        "files_indexed": len(idx["files"]),
        "scanned": scanned, "reused_unchanged": reused,
        "symbols": len(idx["symbols"]), "called_names": len(idx["callers"]),
        "note": "lightweight map (defs+calls). Use --callers/--defs to query. "
                "Cross-module review consults this before claiming a change is local."
    }))

if __name__ == "__main__":
    main()
