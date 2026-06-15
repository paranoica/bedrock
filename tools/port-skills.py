#!/usr/bin/env python3
"""
port-skills.py — make a Claude Code skill available to an agent that uses the open Agent Skills
standard at a DIFFERENT root. OpenAI Codex (verified) loads skills from `.agents/skills/`, not
`.claude/skills/`, and does not understand Claude-only `SKILL.md` frontmatter.

This copies a skill folder to the destination and rewrites `SKILL.md`'s frontmatter, dropping the
Claude-only keys (`allowed-tools`, `disallowed-tools`, `model`, `arguments`, `argument-hint`, `color`)
that other agents don't understand. `references/` and `scripts/` are copied unchanged.

The copy is a GENERATED MIRROR (a `.ported-from-claude` marker is written) — re-run after editing the
source skill; it is not a live link.

Which skills to port for Codex: the consume-side skills — **prompt-refiner**, **code-review**,
**design-creator**. **genesis** runs in Claude Code (it is the inception front door and references
`.claude/...` paths); other agents consume its output (AGENTS.md + the committed scripts), they don't
re-run genesis.

Usage:
  port-skills.py <skill-name> [--root .] [--dest .agents/skills]
  port-skills.py --all        [--root .] [--dest .agents/skills]
"""
import os, sys, re, shutil, argparse

CLAUDE_ONLY = {"allowed-tools", "disallowed-tools", "model", "arguments", "argument-hint", "color"}


def rewrite_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return text  # no frontmatter — copy as-is
    fm, body = m.group(1), m.group(2)
    kept = [ln for ln in fm.split("\n") if ln.split(":", 1)[0].strip() not in CLAUDE_ONLY]
    return "---\n" + "\n".join(kept) + "\n---\n" + body


def port(skill, root, dest):
    src = os.path.join(root, ".claude", "skills", skill)
    if not os.path.isdir(src):
        print("  skip: no such skill at", src)
        return 1
    out = os.path.join(root, dest, skill)
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    sm = os.path.join(out, "SKILL.md")
    if os.path.exists(sm):
        src_text = open(sm, encoding="utf-8").read()   # read BEFORE opening for write (which truncates)
        with open(sm, "w", encoding="utf-8") as f:
            f.write(rewrite_frontmatter(src_text))
    with open(os.path.join(out, ".ported-from-claude"), "w") as f:
        f.write("Generated mirror of .claude/skills/%s by tools/port-skills.py — re-run after edits.\n" % skill)
    print("  ported:", os.path.relpath(src, root), "->", os.path.relpath(out, root))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--root", default=".")
    ap.add_argument("--dest", default=".agents/skills")
    a = ap.parse_args()
    sk_dir = os.path.join(a.root, ".claude", "skills")
    skills = sorted(os.listdir(sk_dir)) if a.all else ([a.skill] if a.skill else [])
    if not skills:
        print("usage: port-skills.py <skill-name> | --all   [--root .] [--dest .agents/skills]")
        sys.exit(2)
    rc = 0
    for s in skills:
        rc |= port(s, a.root, a.dest)
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
