#!/usr/bin/env python3
"""
build.py — a skill-agnostic structural map of a repository, so any skill (genesis,
code-review, …) reads the map instead of re-deriving the project from scratch, and
can tell when the map is stale.

Generalized from code-review/scripts/build_index.py. Beyond that script's defs/calls
map it adds two subsystems the template depends on:

  - FRESHNESS (a tree-level stamp). git HEAD + an aggregate content hash over every
    mapped source file, so staleness — including UNCOMMITTED edits and added/removed
    files — is detectable. `--check` reports fresh|stale|absent without re-parsing.

  - DOMAIN SLICES (routes / data-model / fsm / queues). Best-effort, framework-pattern
    detection, carried as *leads to read, not facts*: every item cites file:line + the
    matched evidence + a confidence, and the slice itself states the verify discipline.

Discipline (carried over from build_index.py, made explicit here and in CONTRACT.md):
  - Map EDGES and SLICE ITEMS are leads to read, never facts on their own.
  - A stale map is never served as fact — callers run `--check` first and rebuild.
  - A weakly-detected slice is marked confidence:"low", not dropped — low-confidence is
    a useful honest lead; absent means "no lead found", not "nothing exists".
  - stdlib only. Read-only on the repo except the output file. Python via `ast`
    (accurate); other languages via regex (good-enough defs/calls, not a full parse).

Usage:
  build.py <root> [--out .map/project.json] [--force]    # build (incremental by default)
  build.py <root> --check                                # freshness probe (JSON; exit 0/1/2)
  build.py <root> --callers <symbol>                     # reverse edge: files that call it
  build.py <root> --defs <symbol>                        # forward edge: files that define it
  build.py <root> --slice routes|data_model|fsm|queues   # dump one domain slice

Exit codes: build/query → 0. --check → 0 fresh, 1 stale, 2 absent (so callers gate).
"""
import sys, os, json, ast, re, hashlib, argparse, subprocess

MAP_VERSION = 1

PY_EXT = {".py"}
JS_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
GO_EXT = {".go"}
C_EXT = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
CS_EXT = {".cs"}
JVM_EXT = {".java", ".kt", ".kts"}
PHP_EXT = {".php"}
RUST_EXT = {".rs"}
RUBY_EXT = {".rb"}
PRISMA_EXT = {".prisma"}   # mapped for SLICES only (no defs/calls language)

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".next", ".nuxt", "vendor", ".mypy_cache", ".pytest_cache", "target",
             "bin", "obj", ".gradle", "coverage", ".turbo", ".svelte-kit",
             # this template's own rebuildable/state dirs — never map them
             ".map", ".genesis", ".design", ".review"}


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ===========================================================================
# DEFS (functions/classes/methods) + CALLS. Python via ast; the rest regex.
# Lifted verbatim from code-review/scripts/build_index.py (proven), so the map
# answers "who calls X?" (reverse) and "where is X defined?" (forward).
# ===========================================================================
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


JS_DEF = re.compile(
    r"(?:function\s+([A-Za-z_$][\w$]*))"
    r"|(?:class\s+([A-Za-z_$][\w$]*))"
    r"|(?:(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)"
    r"|(?:^\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{)",
    re.M)
JS_CALL = re.compile(r"(?:\.|\b)([A-Za-z_$][\w$]*)\s*\(")
JS_KW = {"if", "for", "while", "switch", "catch", "return", "function", "typeof",
         "await", "super", "this", "constructor"}


def parse_js(src):
    defs, calls = set(), set()
    for m in JS_DEF.finditer(src):
        for g in m.groups():
            if g and g not in JS_KW:   # the bare-method-shorthand arm matches `if (...) {` etc; keep keywords out of defs
                defs.add(g)
    for m in JS_CALL.finditer(src):
        name = m.group(1)
        if name not in JS_KW:
            calls.add(name)
    return defs, calls, "js"


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
    return set(GO_DEF.findall(src)), _calls(src), "go"


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


CFAM_DEF = re.compile(
    r"(?:^|[;{}\s])(?:[A-Za-z_][\w:<>,*&\[\]\s]+?\s+)([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:throws[^{;]*)?\{",
    re.M)
KOTLIN_DEF = re.compile(r"\bfun\s+(?:<[^>]*>\s*)?(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)\s*\(", re.M)
TYPE_DEF = re.compile(r"\b(?:class|struct|interface|enum|record|object)\s+([A-Za-z_]\w*)", re.M)
def parse_cfamily(src, lang, extra_kw=frozenset()):
    defs = set(m.group(1) for m in CFAM_DEF.finditer(src))
    defs |= set(KOTLIN_DEF.findall(src))
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
    if ext in PRISMA_EXT: return "prisma"
    return None


def parse_defs_calls(src, ext_lang):
    if ext_lang == "py":   return parse_python(src)
    if ext_lang == "js":   return parse_js(src)
    if ext_lang == "go":   return parse_go(src)
    if ext_lang == "rust": return parse_rust(src)
    if ext_lang == "php":  return parse_php(src)
    if ext_lang == "ruby": return parse_ruby(src)
    if ext_lang in ("c", "cs", "jvm"): return parse_cfamily(src, ext_lang)
    return set(), set(), ext_lang   # prisma / unknown: slices only


# ===========================================================================
# DOMAIN SLICES — best-effort, framework-pattern based. LEADS TO READ, NOT FACTS.
# confidence: "high" = a recognized framework marker matched; "low" = a heuristic
# shape that is worth reading but easily a false positive.
# ===========================================================================
SLICE_NAMES = ("routes", "data_model", "fsm", "queues")
SLICE_DISCIPLINE = "leads to read, not facts — open file:line and confirm before relying"
_HTTP = "get|post|put|patch|delete|head|options"

PY_DECOR_ROUTE = re.compile(r"@\s*[\w.]+\.(%s|route)\s*\(\s*['\"]([^'\"]+)['\"]" % _HTTP)
DJANGO_PATH = re.compile(r"\b(?:re_)?path\s*\(\s*r?['\"]([^'\"]*)['\"]\s*,\s*([\w.]+)")
JS_ROUTE = re.compile(r"\b(?:app|router|api|server|fastify)\.(%s|all)\s*\(\s*['\"]([^'\"]+)['\"]" % _HTTP)
# NestJS / decorator routers: @Get('x'), @Post(), … (path optional — inherited from @Controller)
NEST_ROUTE = re.compile(r"@(Get|Post|Put|Patch|Delete|All|Options|Head)\s*\(\s*(?:['\"]([^'\"]*)['\"])?")
# Spring (Java/Kotlin): @GetMapping("/x"), @RequestMapping(value="/x")
SPRING_ROUTE = re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\s*\(\s*(?:(?:value|path)\s*=\s*)?(?:['\"]([^'\"]*)['\"])?")
# Go routers (gin/echo/gorilla/chi): r.GET("/x", …) — uppercase verb idiom
GO_ROUTE = re.compile(r"\b\w+\.(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\(\s*['\"]([^'\"]+)['\"]")


def _hit(rel, line, evidence, conf, **extra):
    h = {"file": rel, "line": line, "evidence": evidence.strip()[:160], "confidence": conf}
    h.update({k: v for k, v in extra.items() if v is not None})
    return h


def detect_routes(rel, lines, lang):
    hits = []
    is_django_urls = os.path.basename(rel) == "urls.py"
    norm = rel.replace("\\", "/")
    for i, ln in enumerate(lines, 1):
        if lang == "py":
            m = PY_DECOR_ROUTE.search(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", method=m.group(1).upper(), path=m.group(2)))
                continue
            if is_django_urls:
                m = DJANGO_PATH.search(ln)
                if m:
                    hits.append(_hit(rel, i, ln, "high", method="ANY", path=m.group(1), handler=m.group(2)))
        elif lang == "js":
            m = JS_ROUTE.search(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", method=m.group(1).upper(), path=m.group(2)))
                continue
            m = NEST_ROUTE.search(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", method=m.group(1).upper(), path=(m.group(2) or "")))
        elif lang == "jvm":
            m = SPRING_ROUTE.search(ln)
            if m:
                verb = m.group(1).upper()
                hits.append(_hit(rel, i, ln, "high",
                                 method=("ANY" if verb == "REQUEST" else verb), path=(m.group(2) or "")))
        elif lang == "go":
            m = GO_ROUTE.search(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", method=m.group(1), path=m.group(2)))
    # file-based routing (structural, low confidence)
    if lang == "js" and (re.search(r"(^|/)pages/api/.+\.[tj]sx?$", norm)
                         or re.search(r"(^|/)app/.+/route\.[tj]sx?$", norm)):
        hits.append(_hit(rel, 1, "file-based route (Next.js convention)", "low",
                         method="FILE", path="/" + norm))
    return hits


PY_CLASS = re.compile(r"class\s+(\w+)\s*\(([^)]*)\)\s*:")
ORM_BASES = ("Base", "db.Model", "models.Model", "DeclarativeBase", "SQLModel")
PRISMA_MODEL = re.compile(r"^\s*model\s+(\w+)\s*\{")
TS_ENTITY = re.compile(r"@Entity\s*\(")
TS_CLASS = re.compile(r"(?:export\s+)?class\s+(\w+)")
MONGOOSE = re.compile(r"\bnew\s+(?:mongoose\.)?Schema\s*\(")


def detect_data_model(rel, lines, lang):
    hits = []
    pending_entity = False
    for i, ln in enumerate(lines, 1):
        if lang == "prisma":
            m = PRISMA_MODEL.match(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", name=m.group(1), kind="prisma-model"))
            continue
        if lang == "py":
            m = PY_CLASS.search(ln)
            if m:
                name, bases = m.group(1), m.group(2)
                if any(b in bases for b in ORM_BASES):
                    hits.append(_hit(rel, i, ln, "high", name=name, kind="orm-model"))
                elif "BaseModel" in bases:
                    hits.append(_hit(rel, i, ln, "low", name=name, kind="pydantic-schema"))
        elif lang == "js":
            if TS_ENTITY.search(ln):
                pending_entity = True
                continue
            if pending_entity:
                m = TS_CLASS.search(ln)
                if m:
                    hits.append(_hit(rel, i, ln, "high", name=m.group(1), kind="typeorm-entity"))
                    pending_entity = False
            if MONGOOSE.search(ln):
                hits.append(_hit(rel, i, ln, "high", name="(schema)", kind="mongoose-schema"))
    return hits


PY_FSM = re.compile(r"class\s+(\w+)\s*\(([^)]*)\)")
FSM_BASES = ("StateMachine", "Machine")
XSTATE = re.compile(r"\b(?:createMachine|createActor)\s*\(")


def detect_fsm(rel, lines, lang):
    # Library-based only — heuristic status-enums are too noisy to be honest leads.
    hits = []
    head = "\n".join(lines[:60]).lower()
    has_sm_lib = ("statemachine" in head) or ("from transitions" in head) or ("import transitions" in head)
    for i, ln in enumerate(lines, 1):
        if lang == "py" and has_sm_lib:
            m = PY_FSM.search(ln)
            if m and any(b in m.group(2) for b in FSM_BASES):
                hits.append(_hit(rel, i, ln, "high", name=m.group(1), kind="statemachine-lib"))
        elif lang == "js":
            if XSTATE.search(ln):
                hits.append(_hit(rel, i, ln, "high", name="(machine)", kind="xstate"))
    return hits


PY_CELERY = re.compile(r"@\s*(?:shared_task\b|[\w.]+\.task\b)")
PY_RQ = re.compile(r"\.enqueue(?:_call|_at|_in)?\s*\(")
JS_BULL = re.compile(r"\bnew\s+(?:Queue|Worker)\s*\(\s*['\"]?([^'\",)]*)")
JS_NEST = re.compile(r"@\s*(?:Processor|Process)\s*\(")


def detect_queues(rel, lines, lang):
    hits = []
    for i, ln in enumerate(lines, 1):
        if lang == "py":
            if PY_CELERY.search(ln):
                hits.append(_hit(rel, i, ln, "high", kind="celery-task"))
            elif PY_RQ.search(ln):
                hits.append(_hit(rel, i, ln, "low", kind="rq-enqueue"))
        elif lang == "js":
            m = JS_BULL.search(ln)
            if m:
                hits.append(_hit(rel, i, ln, "high", kind="bullmq", name=(m.group(1) or None)))
            elif JS_NEST.search(ln):
                hits.append(_hit(rel, i, ln, "high", kind="nest-processor"))
    return hits


SLICE_DETECTORS = {"routes": detect_routes, "data_model": detect_data_model,
                   "fsm": detect_fsm, "queues": detect_queues}


def parse_slices(rel, src, ext_lang):
    lines = src.splitlines()
    out = {}
    for name, fn in SLICE_DETECTORS.items():
        hits = fn(rel, lines, ext_lang)
        if hits:
            out[name] = hits
    return out


def parse_file(rel, src, ext_lang):
    defs, calls, plang = parse_defs_calls(src, ext_lang)
    return {"hash": None, "lang": plang,
            "defs": sorted(defs), "calls": sorted(calls),
            "slices": parse_slices(rel, src, ext_lang)}


# ===========================================================================
# FRESHNESS — the tree-level stamp. tree_hash is the AUTHORITATIVE signal
# (changes iff any mapped file's content changes, or files are added/removed,
# whether committed or not). git_head/git_dirty are diagnostics.
# ===========================================================================
def _git(root, args):
    try:
        r = subprocess.run(["git", "-C", root] + args,
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def git_info(root):
    if _git(root, ["rev-parse", "--is-inside-work-tree"]) != "true":
        return None, None
    head = _git(root, ["rev-parse", "HEAD"]) or None
    dirty = bool(_git(root, ["status", "--porcelain"]))
    return head, dirty


def aggregate_tree_hash(pairs):
    """sha256 over sorted (relpath, filehash) pairs → 16-hex tree stamp."""
    h = hashlib.sha256()
    for rel, fh in sorted(pairs):
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update((fh or "").encode("utf-8")); h.update(b"\n")
    return h.hexdigest()[:16]


def compute_stamp(root, files):
    head, dirty = git_info(root)
    pairs = [(rel, info.get("hash")) for rel, info in files.items()]
    return {"git_head": head, "git_dirty": dirty,
            "tree_hash": aggregate_tree_hash(pairs),
            "file_count": len(files)}


def iter_sources(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            full = os.path.join(dp, fn)
            if lang_of(full):
                yield full


def aggregate_slices(files):
    agg = {}
    for name in SLICE_NAMES:
        items = []
        for info in files.values():
            items.extend(info.get("slices", {}).get(name, []))
        if not items:
            continue
        items.sort(key=lambda x: (x.get("file", ""), x.get("line", 0)))
        conf = "high" if any(it.get("confidence") == "high" for it in items) else "low"
        agg[name] = {"confidence": conf, "count": len(items),
                     "discipline": SLICE_DISCIPLINE, "items": items}
    return agg


def build(root, out_path, force=False):
    prev = {}
    if os.path.exists(out_path) and not force:
        try:
            old = json.load(open(out_path))
            if old.get("version") == MAP_VERSION:
                prev = old.get("files", {})
        except Exception:
            prev = {}
    files = {}
    reused = scanned = 0
    for full in iter_sources(root):
        rel = os.path.relpath(full, root).replace("\\", "/")
        try:
            h = file_hash(full)
        except OSError:
            continue
        cached = prev.get(rel)
        if cached and cached.get("hash") == h and "slices" in cached:
            files[rel] = cached
            reused += 1
            continue
        try:
            src = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rec = parse_file(rel, src, lang_of(full))
        rec["hash"] = h
        files[rel] = rec
        scanned += 1

    symbols, callers = {}, {}
    for rel, info in files.items():
        for d in info.get("defs", []):
            symbols.setdefault(d, []).append(rel)
        for c in info.get("calls", []):
            callers.setdefault(c, []).append(rel)

    index = {"version": MAP_VERSION, "root": os.path.abspath(root),
             "stamp": compute_stamp(root, files),
             "files": files,
             "symbols": {k: sorted(set(v)) for k, v in symbols.items()},
             "callers": {k: sorted(set(v)) for k, v in callers.items()},
             "slices": aggregate_slices(files)}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(index, f, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, out_path)   # atomic: a reader never sees a half-written map
    return index, scanned, reused


def check(root, out_path):
    """Freshness probe — re-hash current files and compare the tree stamp. No parse."""
    if not os.path.exists(out_path):
        return {"state": "absent", "reason": "no map at %s; run a build first" % out_path}
    try:
        old = json.load(open(out_path))
    except Exception as e:
        return {"state": "absent", "reason": "map unreadable (%s); rebuild" % e}
    if old.get("version") != MAP_VERSION:
        return {"state": "stale", "reason": "map schema v%s != current v%s"
                % (old.get("version"), MAP_VERSION)}
    prev_files = old.get("files", {})
    cur = {}
    for full in iter_sources(root):
        rel = os.path.relpath(full, root).replace("\\", "/")
        try:
            cur[rel] = file_hash(full)
        except OSError:
            continue
    now_tree = aggregate_tree_hash(cur.items())
    map_tree = old.get("stamp", {}).get("tree_hash")
    if now_tree == map_tree:
        return {"state": "fresh", "tree_hash": now_tree, "file_count": len(cur)}
    changed = sorted(r for r in cur if cur[r] != prev_files.get(r, {}).get("hash"))
    removed = sorted(set(prev_files) - set(cur))
    return {"state": "stale", "reason": "mapped files changed since the stamp",
            "tree_hash_now": now_tree, "tree_hash_map": map_tree,
            "changed_files": changed[:50], "changed_count": len(changed),
            "removed_files": removed[:50], "removed_count": len(removed),
            "hint": "incremental rebuild touches only changed files"}


def main():
    ap = argparse.ArgumentParser(description="skill-agnostic repo map + freshness stamp")
    ap.add_argument("root")
    ap.add_argument("--out", default=".map/project.json")
    ap.add_argument("--force", action="store_true", help="ignore cache; full rebuild")
    ap.add_argument("--check", action="store_true",
                    help="freshness probe; exit 0 fresh / 1 stale / 2 absent")
    ap.add_argument("--callers", metavar="SYMBOL", help="files that CALL this symbol")
    ap.add_argument("--defs", metavar="SYMBOL", help="files that DEFINE this symbol")
    ap.add_argument("--slice", metavar="NAME", choices=SLICE_NAMES, help="dump one domain slice")
    a = ap.parse_args()
    out = a.out if os.path.isabs(a.out) else os.path.join(a.root, a.out)

    if a.check:
        res = check(a.root, out)
        print(json.dumps(res, indent=2))
        sys.exit({"fresh": 0, "stale": 1, "absent": 2}.get(res["state"], 2))

    if a.callers or a.defs or a.slice:
        if not os.path.exists(out):
            print(json.dumps({"error": "no map; build first (run without query flags)"}))
            sys.exit(2)
        idx = json.load(open(out))
        unchecked = "unchecked — run --check first; this query does not self-verify freshness"
        if a.callers:
            print(json.dumps({"symbol": a.callers,
                              "callers": idx.get("callers", {}).get(a.callers, []),
                              "_note": "leads to read, not facts — open each file and confirm",
                              "freshness": unchecked}, indent=2))
        elif a.defs:
            print(json.dumps({"symbol": a.defs,
                              "defs": idx.get("symbols", {}).get(a.defs, []),
                              "_note": "leads to read, not facts",
                              "freshness": unchecked}, indent=2))
        else:
            sl = idx.get("slices", {}).get(a.slice)
            out_obj = dict(sl) if sl else {"slice": a.slice, "state": "absent — no leads detected"}
            out_obj["freshness"] = unchecked
            print(json.dumps(out_obj, indent=2))
        return

    idx, scanned, reused = build(a.root, out, force=a.force)
    print(json.dumps({
        "ok": True, "out": out,
        "files_mapped": len(idx["files"]), "scanned": scanned, "reused_unchanged": reused,
        "symbols": len(idx["symbols"]), "called_names": len(idx["callers"]),
        "slices": {k: {"count": v["count"], "confidence": v["confidence"]}
                   for k, v in idx["slices"].items()},
        "stamp": idx["stamp"],
        "note": "map edges + slice items are LEADS TO READ, not facts. Run --check "
                "before relying; never serve a stale map as fact.",
    }, indent=2))


if __name__ == "__main__":
    main()
