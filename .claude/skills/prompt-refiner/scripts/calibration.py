#!/usr/bin/env python3
"""
prompt-refiner calibration — is the gate calibrated? Sparse, DNA-consistent. The asymmetry matters:
the COSTLY error is FALSE INTERCEPTION (refiner took/asked on a request a profile engine could have
started), not false silence (refiner yielded; the engine asks its own question). The report surfaces
false-interception specifically, so a drifting gate that grabs too much is visible.

Outcome semantics (landed = "was this the right call?"):
  decision=yielded  landed=1 the engine handled it (yield was right) | 0 refiner should've taken (false silence)
  decision=took     landed=1 the sharpened prompt/route was right    | 0 an engine could've started (FALSE INTERCEPTION)
  decision=asked    landed=1 the answer changed the work             | 0 the question was unnecessary (FALSE INTERCEPTION)

Commands (--root .):  record <yielded|took|asked> <0|1> [--note S]   |   report
"""
import sys, os, json, argparse

DECISIONS = ("yielded", "took", "asked")


def _log(root):
    return os.path.join(root, ".refiner", "calibration.jsonl")


def cmd_record(root, decision, landed, note):
    if decision not in DECISIONS:
        print(json.dumps({"error": "decision must be one of", "allowed": list(DECISIONS)})); sys.exit(2)
    if landed not in ("0", "1"):
        print(json.dumps({"error": "landed must be 0 or 1"})); sys.exit(2)
    os.makedirs(os.path.join(root, ".refiner"), exist_ok=True)
    row = {"decision": decision, "landed": int(landed)}
    if note:
        row["note"] = note
    with open(_log(root), "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps({"ok": True, **row}))


def cmd_report(root):
    rows = []
    if os.path.exists(_log(root)):
        rows = [json.loads(l) for l in open(_log(root)) if l.strip()]
    took = [r for r in rows if r["decision"] in ("took", "asked")]
    yielded = [r for r in rows if r["decision"] == "yielded"]
    asked = [r for r in rows if r["decision"] == "asked"]
    false_intercept = sum(1 for r in took if r["landed"] == 0)
    false_silence = sum(1 for r in yielded if r["landed"] == 0)
    print(json.dumps({
        "total": len(rows),
        "by_decision": {d: sum(1 for r in rows if r["decision"] == d) for d in DECISIONS},
        "false_interception": false_intercept,   # the COSTLY error — minimize this first
        "false_silence": false_silence,          # the cheap error — tolerated
        "asks": {"n": len(asked), "helped": sum(r["landed"] for r in asked)},
        "boundary": "false interception (grabbed what an engine could start) is the costly error; "
                    "false silence (yielded, engine asked its own question) is cheap and expected. "
                    "A rising false_interception means the residue-test is leaking — tighten the test.",
        "cold_start": "sparse by design — read trends, not single rows.",
    }, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["record", "report"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--root", default=".")
    ap.add_argument("--note", default=None)
    a = ap.parse_args()
    if a.command == "record":
        cmd_record(a.root, a.args[0] if a.args else "", a.args[1] if len(a.args) > 1 else "", a.note)
    else:
        cmd_report(a.root)


if __name__ == "__main__":
    main()
