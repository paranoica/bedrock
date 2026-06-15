#!/usr/bin/env python3
"""
backlog.py — genesis.tasks.json is the SINGLE source of task state; PLAN.md is a GENERATED
render. Task state changes ONLY through this script (never hand-edit either file). Spec-ref
hashes come from anchors.py (never hand-written).

Commands (all take --root <dir>, default "."):
  stamp                 (re)compute each task's spec_refs = forward closure of its declared refs,
                        fill hashes via anchors.py, re-render PLAN.md
  re-derive [--apply]   compare stored spec_refs hashes to current docs; flag tasks:
                          content drift on a surviving ref  -> needs-review (soft)
                          a traced anchor removed/renamed    -> stale (structural; re-derive it)
                        dry-run by default; --apply persists STATUS only (hashes refresh via stamp)
  next                  print the next ready task (status todo, all deps done)
  start <id> / done <id>
  status <id> <state> [--note S]
  validate              DAG cycle check + dangling deps/spec_refs + status sanity (exit 1 on problem)
  render                regenerate PLAN.md from genesis.tasks.json
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchors

DOC_FILES = ["decisions.md", "architecture.md", "glossary.md", "open-questions.md"]
COMMANDS = ("stamp", "re-derive", "next", "start", "done", "status", "validate", "render")
ACTIVE = {"todo", "doing", "done", "stale", "needs-review", "blocked"}
SYM = {"todo": "[ ]", "doing": "[~]", "done": "[x]", "stale": "[!]",
       "needs-review": "[?]", "blocked": "[/]"}
PLAN_BANNER = ("<!-- GENERATED from genesis.tasks.json by backlog.py — DO NOT EDIT BY HAND. "
               "Change task state via: backlog.py status <id> <state> -->")


def doc_paths(root):
    return [os.path.join(root, "docs", d) for d in DOC_FILES
            if os.path.exists(os.path.join(root, "docs", d))]


def load_tasks(root):
    p = os.path.join(root, "genesis.tasks.json")
    return json.load(open(p)), p


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save_tasks(obj, path):
    _atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def plan_text(obj):
    """The canonical render. validate() diffs this against disk so a hand-edit is VISIBLE."""
    lines = [PLAN_BANNER, "", "# Plan — " + obj.get("project", "<project>"), ""]
    by_sprint = {}
    for t in obj["tasks"]:
        by_sprint.setdefault(t.get("sprint", "(unsorted)"), []).append(t)
    for sprint in sorted(by_sprint):
        lines.append("## " + sprint)
        for t in by_sprint[sprint]:
            dep = (" ← " + ", ".join(t["dependencies"])) if t.get("dependencies") else ""
            lines.append("- {m} **{id}** {title}{dep}".format(
                m=SYM.get(t["status"], "[ ]"), id=t["id"], title=t["title"], dep=dep))
            for ac in t.get("acceptance", []):
                lines.append("    - _accept:_ " + ac)
            v = t.get("verify") or {}
            if v.get("kind"):
                lines.append("    - _verify ({k}):_ {h}".format(k=v.get("kind"), h=v.get("handle", "")))
        lines.append("")
    return "\n".join(lines)


def render_plan(obj, root):
    _atomic_write(os.path.join(root, "PLAN.md"), plan_text(obj))


def cmd_stamp(root):
    by_id, dups = anchors.parse_files(doc_paths(root))
    obj, path = load_tasks(root)
    dangling = []
    for t in obj["tasks"]:
        roots = list((t.get("spec_refs") or {}).keys())
        closure = anchors.forward_closure(roots, by_id)
        sr = {}
        for aid in sorted(closure):
            rec = by_id.get(aid)
            sr[aid] = rec["hash"] if rec else None
            if rec is None:
                dangling.append({"task": t["id"], "ref": aid})
        t["spec_refs"] = sr
    save_tasks(obj, path)
    render_plan(obj, root)
    print(json.dumps({"ok": True, "tasks": len(obj["tasks"]),
                      "dangling": dangling, "duplicate_anchors": dups}, indent=2))


def cmd_rederive(root, apply_changes):
    by_id, _ = anchors.parse_files(doc_paths(root))
    cur = {aid: rec["hash"] for aid, rec in by_id.items()}
    obj, path = load_tasks(root)
    changes = []
    for t in obj["tasks"]:
        sr = t.get("spec_refs") or {}
        gone = sorted(aid for aid in sr if aid not in cur)
        drift = sorted(aid for aid in sr if aid in cur and sr[aid] != cur[aid])
        if not gone and not drift:
            continue
        if gone:                      # structural: a traced anchor disappeared
            new = "needs-review" if t["status"] == "done" else "stale"
            reason = "structural — anchor removed/renamed: " + ", ".join(gone)
        else:                         # content drift only
            new = "needs-review"
            reason = "content drift: " + ", ".join(drift)
        changes.append({"task": t["id"], "from": t["status"], "to": new,
                        "reason": reason, "gone": gone, "drift": drift})
        if apply_changes:
            t["status"] = new         # STATUS only; hashes refresh via `stamp` after review
    if apply_changes and changes:
        save_tasks(obj, path)
        render_plan(obj, root)
    print(json.dumps({"mode": "apply" if apply_changes else "dry-run",
                      "summary": {"changed": len(changes),
                                  "needs_review": sum(c["to"] == "needs-review" for c in changes),
                                  "stale": sum(c["to"] == "stale" for c in changes)},
                      "changes": changes}, indent=2))


def cmd_next(root):
    obj, _ = load_tasks(root)
    done = {t["id"] for t in obj["tasks"] if t["status"] == "done"}
    ready = [t for t in obj["tasks"]
             if t["status"] == "todo" and all(d in done for d in t.get("dependencies", []))]
    print(json.dumps(ready[0] if ready else {"state": "none ready"}, indent=2, ensure_ascii=False))


def cmd_status(root, tid, state, note):
    if state not in ACTIVE:
        print(json.dumps({"error": "bad state", "allowed": sorted(ACTIVE)})); sys.exit(2)
    obj, path = load_tasks(root)
    t = next((x for x in obj["tasks"] if x["id"] == tid), None)
    if not t:
        print(json.dumps({"error": "no such task", "id": tid})); sys.exit(2)
    if state == "done":
        done = {x["id"] for x in obj["tasks"] if x["status"] == "done"}
        missing = [d for d in t.get("dependencies", []) if d not in done]
        if missing:
            print(json.dumps({"error": "cannot mark done — dependencies not done", "missing": missing}))
            sys.exit(1)
    old = t["status"]
    t["status"] = state
    if note:
        t.setdefault("notes", []).append(note)
    save_tasks(obj, path)
    render_plan(obj, root)
    print(json.dumps({"ok": True, "id": tid, "from": old, "to": state}, indent=2))


def _has_cycle(tasks):
    graph = {t["id"]: list(t.get("dependencies", [])) for t in tasks}
    state = {}

    def dfs(n, path):
        if state.get(n) == 1:
            return path[path.index(n):] + [n]
        if state.get(n) == 2:
            return None
        state[n] = 1
        for d in graph.get(n, []):
            if d in graph:
                r = dfs(d, path + [n])
                if r:
                    return r
        state[n] = 2
        return None

    for n in graph:
        r = dfs(n, [])
        if r:
            return r
    return None


def cmd_validate(root):
    by_id, dups = anchors.parse_files(doc_paths(root))
    obj, _ = load_tasks(root)
    ids = {t["id"] for t in obj["tasks"]}
    problems = []
    for t in obj["tasks"]:
        for d in t.get("dependencies", []):
            if d not in ids:
                problems.append({"task": t["id"], "issue": "dangling dependency", "ref": d})
        for aid in (t.get("spec_refs") or {}):
            if aid not in by_id:
                problems.append({"task": t["id"], "issue": "dangling spec_ref", "ref": aid})
        if t["status"] not in ACTIVE:
            problems.append({"task": t["id"], "issue": "bad status", "value": t["status"]})
    cyc = _has_cycle(obj["tasks"])
    if cyc:
        problems.append({"issue": "dependency cycle", "nodes": cyc})
    if dups:
        problems.append({"issue": "duplicate anchor ids", "dups": dups})
    # PLAN.md consistency — makes a hand-edit of genesis.tasks.json OR PLAN.md a VISIBLE failure
    # (re-render and diff), not a silent drift. This is the teeth behind the canon's status-seam rule.
    plan_path = os.path.join(root, "PLAN.md")
    if not os.path.exists(plan_path):
        problems.append({"issue": "PLAN.md missing — run: backlog.py render"})
    elif open(plan_path, encoding="utf-8").read() != plan_text(obj):
        problems.append({"issue": "PLAN.md out of sync with genesis.tasks.json "
                                  "(hand-edited, or tasks changed without re-render) — run: backlog.py render"})
    print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
    sys.exit(1 if problems else 0)


def main():
    ap = argparse.ArgumentParser(description="genesis backlog: state via this script only")
    ap.add_argument("command", choices=list(COMMANDS))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--root", default=".")
    ap.add_argument("--note", default=None)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    c = a.command
    if c == "stamp":
        cmd_stamp(a.root)
    elif c == "re-derive":
        cmd_rederive(a.root, a.apply)
    elif c == "next":
        cmd_next(a.root)
    elif c == "start":
        cmd_status(a.root, a.args[0], "doing", a.note)
    elif c == "done":
        cmd_status(a.root, a.args[0], "done", a.note)
    elif c == "status":
        cmd_status(a.root, a.args[0], a.args[1], a.note)
    elif c == "validate":
        cmd_validate(a.root)
    elif c == "render":
        obj, _ = load_tasks(a.root)
        render_plan(obj, a.root)
        print(json.dumps({"ok": True, "rendered": "PLAN.md"}))


if __name__ == "__main__":
    main()
