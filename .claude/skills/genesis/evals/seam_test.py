#!/usr/bin/env python3
"""
Regression test for the anchor/normalizer SEAM + the spec-analyze gate teeth — the live demos made
permanent. Self-contained: copies the fixture to a temp dir, runs each scenario, asserts the exact
expected outcome. A change to normalize()/backlog/analyze that breaks the seam fails here.

Run: python3 .claude/skills/genesis/evals/seam_test.py
"""
import os, sys, json, shutil, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.normpath(os.path.join(HERE, "..", "scripts"))
FIX = os.path.join(HERE, "fixtures", "storage-marketplace")
PY = sys.executable
fails = []


def run(script, *args):
    r = subprocess.run([PY, os.path.join(SK, script), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def jrun(script, *args):
    rc, out, err = run(script, *args)
    try:
        return rc, json.loads(out)
    except Exception:
        return rc, {"_raw": out, "_err": err}


def check(name, cond, detail=""):
    print(("  ok  " if cond else "FAIL ") + name + (("  — " + detail) if (not cond and detail) else ""))
    if not cond:
        fails.append(name)


def edit(path, old, new):
    s = open(path).read()
    assert old in s, "edit target missing: " + old
    open(path, "w").write(s.replace(old, new))


def docs(root):
    return [os.path.join(root, "docs", d) for d in
            ["decisions.md", "glossary.md", "architecture.md", "open-questions.md"]]


def main():
    tmp = tempfile.mkdtemp(prefix="genesis-seam-")
    root = os.path.join(tmp, "proj")
    shutil.copytree(FIX, root)
    dec = os.path.join(root, "docs", "decisions.md")
    glo = os.path.join(root, "docs", "glossary.md")

    _, a1 = jrun("anchors.py", *docs(root))
    _, a2 = jrun("anchors.py", *docs(root))
    check("anchors deterministic across runs", a1 == a2)

    run("backlog.py", "--root", root, "stamp")
    t010 = next(t for t in json.load(open(os.path.join(root, "genesis.tasks.json")))["tasks"] if t["id"] == "T010")
    check("stamp expands closure (T010 gets term:escrow + open payment-provider)",
          "term:escrow" in t010["spec_refs"] and "decision:payment-provider" in t010["spec_refs"])

    _, rd = jrun("backlog.py", "--root", root, "re-derive")
    check("zero-drift on a freshly stamped spec", rd["summary"]["changed"] == 0)

    edit(dec, "monthly minus commission", "monthly minus a commission fee")
    _, rd = jrun("backlog.py", "--root", root, "re-derive")
    chg = {c["task"]: c["to"] for c in rd["changes"]}
    check("CONTENT edit -> T010 needs-review (not stale)", chg.get("T010") == "needs-review", str(chg))
    edit(dec, "monthly minus a commission fee", "monthly minus commission")

    edit(dec, "Phone login is out.", "**Phone login is out.**")
    _, rd = jrun("backlog.py", "--root", root, "re-derive")
    check("FORMATTING-only edit -> zero drift (normalizer earns its keep)", rd["summary"]["changed"] == 0)
    edit(dec, "**Phone login is out.**", "Phone login is out.")

    edit(dec, "@anchor decision:auth-model", "@anchor decision:auth")
    _, rd = jrun("backlog.py", "--root", root, "re-derive")
    chg = {c["task"]: c["to"] for c in rd["changes"]}
    check("STRUCTURAL rename -> T003 stale", chg.get("T003") == "stale", str(chg))
    check("STRUCTURAL rename -> done T001 needs-review (protected)", chg.get("T001") == "needs-review", str(chg))
    edit(dec, "@anchor decision:auth", "@anchor decision:auth-model")

    edit(glo, "pending payout.", "pending payout (held in trust).")
    _, rd = jrun("backlog.py", "--root", root, "re-derive")
    chg = {c["task"]: c["to"] for c in rd["changes"]}
    check("TRANSITIVE term:escrow edit -> T010 needs-review", chg.get("T010") == "needs-review", str(chg))
    edit(glo, "pending payout (held in trust).", "pending payout.")

    rc, an = jrun("analyze_spec.py", root)
    check("clean spec -> 0 CRITICAL", an["summary"]["CRITICAL"] == 0)
    check("T010 flagged HIGH rests-on-open-decision",
          any(f["code"] == "rests-on-open-decision" for f in an["findings"]))

    # F-A: the gate receipt has teeth — --check detects a spec change made AFTER the gate ran
    rc, _, _ = run("analyze_spec.py", root, "--check")
    check("spec-receipt fresh right after the gate ran", rc == 0)
    edit(dec, "monthly minus commission", "monthly minus a COMMISSION fee")
    rc, _, _ = run("analyze_spec.py", root, "--check")
    check("spec edited after the gate -> receipt stale (exit 1)", rc == 1)
    edit(dec, "monthly minus a COMMISSION fee", "monthly minus commission")

    with open(dec, "a") as f:
        f.write("\n### D-9 deliberately unanchored\n- x\n")
    rc, an = jrun("analyze_spec.py", root)
    check("PARTIAL annotation -> CRITICAL + exit 1", rc == 1 and an["summary"]["CRITICAL"] >= 1)
    s = open(dec).read(); open(dec, "w").write(s.replace("\n### D-9 deliberately unanchored\n- x\n", ""))

    run("backlog.py", "--root", root, "render")
    rc, _, _ = run("backlog.py", "--root", root, "validate")
    check("validate clean -> exit 0", rc == 0)
    with open(os.path.join(root, "PLAN.md"), "a") as f:
        f.write("\nhand-added junk\n")
    rc, _, _ = run("backlog.py", "--root", root, "validate")
    check("hand-edit PLAN.md -> validate exit 1 (status seam has teeth)", rc == 1)

    shutil.rmtree(tmp)
    print("\nSEAM REGRESSION: " + ("PASS" if not fails else "FAIL " + str(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
