"""Copy the humanize skill and its draft trigger from claude-humanize-skill into the plugin.

The skill lives in its own repository; bedrock carries a copy so that a fresh install has
it. Edit the skill there, then run this. Only files tracked in that repository are copied,
so a voice profile never reaches bedrock. The frontmatter description is taken from
`skill/description-short.txt`, which fits the plugin's description budget.

Usage:
    python3 tools/sync_humanize.py [--source DIR] [--check]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "bedrock" / "skills" / "humanize"
TRIGGER = ROOT / "plugins" / "bedrock" / "scripts" / "bedrock_hooks" / "draft_trigger.py"
DEFAULT_SOURCE = ROOT.parent / "claude-humanize-skill"
SKIPPED = {"skill/description-short.txt"}
DESCRIPTION = re.compile(r"^description:.*?(?=^\w[\w-]*:|^---)", re.M | re.S)


def _git(source: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def wanted(source: Path) -> dict[Path, bytes]:
    """Every file the plugin should hold, by its path in bedrock."""
    files: dict[Path, bytes] = {}
    for rel in _git(source, "ls-files", "skill").splitlines():
        if rel in SKIPPED:
            continue
        files[SKILL / rel.removeprefix("skill/")] = (source / rel).read_bytes()
    short = (source / "skill" / "description-short.txt").read_text(encoding="utf-8").strip()
    skill_md = SKILL / "SKILL.md"
    text = files[skill_md].decode("utf-8")
    files[skill_md] = DESCRIPTION.sub(lambda _: f"description: {short}\n", text, 1).encode()
    files[TRIGGER] = (source / "hooks" / "draft_trigger.py").read_bytes()
    commit = _git(source, "rev-parse", "HEAD").strip()
    files[SKILL / "SOURCE"] = (
        f"https://github.com/paranoica/claude-humanize-skill at {commit}\n"
        "Copied by tools/sync_humanize.py; edit it there, not here.\n"
    ).encode()
    return files


def present() -> dict[Path, bytes]:
    """What the plugin holds now."""
    found = {p: p.read_bytes() for p in SKILL.rglob("*") if p.is_file()}
    if TRIGGER.exists():
        found[TRIGGER] = TRIGGER.read_bytes()
    return {p: data for p, data in found.items() if "__pycache__" not in p.parts}


def main(argv: list[str] | None = None) -> int:
    """Write the copy, or with --check report whether it is current."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--check", action="store_true", help="exit 1 when the copy is stale")
    args = parser.parse_args(argv)
    if not (args.source / "skill" / "SKILL.md").is_file():
        print(f"no claude-humanize-skill at {args.source}", file=sys.stderr)
        return 2
    target = wanted(args.source)
    current = present()
    stale = sorted(
        str(p.relative_to(ROOT))
        for p in target.keys() | current.keys()
        if target.get(p) != current.get(p)
    )
    if args.check:
        for path in stale:
            print(f"stale: {path}")
        return 1 if stale else 0
    if SKILL.exists():
        shutil.rmtree(SKILL)
    for path, data in target.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"copied {len(target)} files from {args.source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
