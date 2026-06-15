#!/usr/bin/env python3
"""
drift-check.py — fails (NON-ZERO) when canon <-> project-map CONTRACT <-> genesis DISAGREE — not
merely when a file is missing. Presence is the weak test; this checks CONSISTENCY.

Single source of the canonical paths/commands/anchor facts is `tools/contract.json`. This check reads
VALUES from there and never keeps a second hardcoded path list (that would make the drift-checker the
very carrier of the drift it cures). The phase-5 inter-skill contract doc documents the same file.

Four named semantic linkages (teeth, not vibes):
  L1  MAP PATH         — contract's map path appears in build.py (its --out default), in the
                         project-map CONTRACT.md, and in genesis/index.json. Change it in one -> FAIL.
  L2  GATE COMMANDS    — each command in the contract is (a) really implemented (backlog.COMMANDS /
                         a flag in the script) AND (b) referenced by the canon template. Dead mandate
                         reference, or a renamed command the mandate still cites -> FAIL.
  L3  ANCHOR FACTS     — the cross-cutting anchor set agrees across contract.json, anchors.py
                         (CROSS_CUTTING), and anchor-contract.md (types documented). Change one -> FAIL.
  L4  DESIGN BRIEF     — the genesis->design-creator brief path in contract.json matches
                         design-handoff.md. Path drifts between the two -> FAIL.

Blocking: exit 1 on any disagreement. Run it in the template's own evals / CI.
"""
import os, sys, json, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
GEN = os.path.join(ROOT, ".claude", "skills", "genesis")


def rp(*a):
    return os.path.join(ROOT, *a)


def read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return None


def main():
    problems = []

    def need(cond, msg):
        if not cond:
            problems.append(msg)

    contract = json.load(open(rp("tools", "contract.json")))
    paths, cmds, anchor = contract["paths"], contract["commands"], contract["anchor"]

    # ---- L1 — MAP PATH agreement (the "change CONTRACT's path -> FAIL" test) ----
    mp = paths["map"]
    need(mp in (read(rp(paths["map_tool"])) or ""),
         "L1 map path %r missing from %s (build.py --out default drifted)" % (mp, paths["map_tool"]))
    need(mp in (read(rp(paths["map_contract"])) or ""),
         "L1 map path %r missing from %s (CONTRACT drifted)" % (mp, paths["map_contract"]))
    need(mp in (read(os.path.join(GEN, "index.json")) or ""),
         "L1 map path %r missing from genesis/index.json (state map drifted)" % mp)

    # ---- L2 — GATE COMMANDS: AGENTS.md's @bedrock-contract region lists EXACTLY the contract's
    #          commands (machine-parsed region, not prose), and each command is implemented. ----
    agents_md = read(rp(paths["canon"])) or ""   # AGENTS.md is the canonical rules file
    m_region = re.search(r"<!--\s*@bedrock-contract\b(.*?)-->", agents_md, re.S)
    region = m_region.group(1) if m_region else ""
    need(bool(m_region), "L2 AGENTS.md has no @bedrock-contract region — gate mandates not machine-checkable")
    sys.path.insert(0, os.path.join(GEN, "scripts"))
    import backlog  # noqa: E402  (authoritative COMMANDS tuple)
    canonical = {}   # canonical command string -> contract key
    for key, c in cmds.items():
        cstr = os.path.basename(c["script"]) + " " + (c.get("cmd") or c.get("flag"))
        canonical[cstr] = key
        if "cmd" in c:   # implemented?
            ok = (c["cmd"] in backlog.COMMANDS) if c["script"].endswith("backlog.py") \
                else (c["cmd"] in (read(rp(c["script"])) or ""))
            need(ok, "L2 command %r (%s) not implemented in %s" % (c["cmd"], key, c["script"]))
        else:
            need(c["flag"] in (read(rp(c["script"])) or ""),
                 "L2 flag %r (%s) not implemented in %s" % (c["flag"], key, c["script"]))
        need(cstr in region, "L2 AGENTS.md @bedrock-contract region missing %r (%s) — mandate not stated" % (cstr, key))
    # region must NOT list extras (region == contract.json, both directions)
    for ln in (l.strip() for l in region.splitlines()):
        if re.match(r"^\S+\.(py|sh|mjs)\s+\S", ln) and ln not in canonical:
            need(False, "L2 AGENTS.md region lists %r — not in contract.json (region drifted)" % ln)

    # ---- L3 — ANCHOR FACTS agreement ----
    import anchors  # noqa: E402
    code_cc = sorted(t.rstrip(":") for t in anchors.CROSS_CUTTING)
    need(code_cc == sorted(anchor["cross_cutting"]),
         "L3 cross-cutting drift: anchors.py %s != contract.json %s" % (code_cc, sorted(anchor["cross_cutting"])))
    ac_md = read(os.path.join(GEN, "references", "anchor-contract.md")) or ""
    for t in anchor["types"]:
        need(t in ac_md, "L3 anchor type %r not documented in anchor-contract.md" % t)

    # ---- L4 — design-brief path agreement (genesis -> design-creator handoff) ----
    bp = paths["design_brief"]
    need(bp in (read(os.path.join(GEN, "references", "design-handoff.md")) or ""),
         "L4 design-brief path %r missing from design-handoff.md (handoff path drifted)" % bp)

    print(json.dumps({"ok": not problems,
                      "linkages": ["L1 map-path", "L2 gate-commands", "L3 anchor-facts", "L4 design-brief"],
                      "problems": problems}, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
