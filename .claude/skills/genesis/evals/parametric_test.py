#!/usr/bin/env python3
"""
Parametricity regression — proves genesis's gate works on a NON-WEB spec, not just the
storage-marketplace fixture it was designed around. Runs the real scripts on
`fixtures/cli-backup` (a backup CLI: no web, no money, no auth) in a temp copy and asserts the
expected gate outcomes — including that the open-decision block does NOT over-fire onto tasks that
don't depend on it, and that no design-brief is produced for a non-web project.

Run: python3 .claude/skills/genesis/evals/parametric_test.py
"""
import os, sys, json, shutil, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.normpath(os.path.join(HERE, "..", "scripts"))
FIX = os.path.join(HERE, "fixtures", "cli-backup")
PY = sys.executable
fails = []


def run(script, *args):
    r = subprocess.run([PY, os.path.join(SK, script), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def jrun(script, *args):
    rc, out = run(script, *args)
    try:
        return rc, json.loads(out)
    except Exception:
        return rc, {"_raw": out}


def check(name, cond, detail=""):
    print(("  ok  " if cond else "FAIL ") + name + (("  — " + detail) if (not cond and detail) else ""))
    if not cond:
        fails.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="genesis-param-")
    root = os.path.join(tmp, "proj")
    shutil.copytree(FIX, root)

    run("backlog.py", "--root", root, "stamp")
    tasks = {t["id"]: t for t in json.load(open(os.path.join(root, "genesis.tasks.json")))["tasks"]}

    check("stamp resolves every ref on a non-web spec (no dangling)",
          all(v is not None for v in tasks["T001"]["spec_refs"].values()))
    check("T001 (local write) does NOT inherit the open remote-backend (no over-firing)",
          "decision:remote-backend" not in tasks["T001"]["spec_refs"])
    check("T004 (remote driver) DOES carry the open remote-backend",
          "decision:remote-backend" in tasks["T004"]["spec_refs"])

    rc, _ = run("backlog.py", "--root", root, "validate")
    check("validate clean -> exit 0", rc == 0)

    rc, an = jrun("analyze_spec.py", root)
    check("non-web spec -> 0 CRITICAL", an["summary"]["CRITICAL"] == 0)
    highs = sorted(f["where"] for f in an["findings"] if f["code"] == "rests-on-open-decision")
    check("exactly T004 rests on the open decision (block doesn't over-fire)", highs == ["T004"], str(highs))

    rc, _ = run("analyze_spec.py", root, "--check")
    check("gate receipt fresh -> exit 0", rc == 0)

    check("project-type=CLI -> NO design-brief emitted",
          not os.path.exists(os.path.join(root, ".genesis", "design-brief.json")))

    shutil.rmtree(tmp)
    print("\nPARAMETRIC (non-web): " + ("PASS" if not fails else "FAIL " + str(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
