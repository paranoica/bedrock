#!/usr/bin/env python3
"""Check the plugin's skills and agent definitions against the writing rules.

Exit codes: 0 clean (warnings allowed unless --strict), 1 a violation, 2 the check could not run.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_LINE_LIMIT = 250
# Skills carried whole from the bedrock main branch keep their own length and sentence style;
# frontmatter, the description budget and links are still checked.
PORTED = {"code-review", "design-creator"}
REFERENCE_LINE_LIMIT = 300
DESCRIPTION_TOKEN_LIMIT = 60
MAX_SEMICOLONS = 2
LONG_SENTENCE_WORDS = 40
AGENT_DESCRIPTION_WORDS = 12
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REFERENCE_PATH_RE = re.compile(r"`(references/[\w./-]+\.md)`")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
EXTERNAL_PREFIXES = ("http://", "https://", "#")


class CheckError(Exception):
    """A file could not be read, so the check cannot run."""


def read(path: Path) -> str:
    """Read a file as UTF-8, tolerating a byte-order mark."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise CheckError(f"cannot read {path}: {error}") from error


@dataclass(frozen=True)
class Finding:
    """One problem found in a file."""

    path: str
    line: int
    level: str
    rule: str
    message: str

    def render(self) -> str:
        """Format the finding as one output line."""
        return f"{self.path}:{self.line}: {self.level} {self.rule}: {self.message}"


class Frontmatter:
    """A minimal YAML frontmatter reader for flat `key: value` and folded `key: >` fields."""

    def __init__(self, fields: dict[str, str], multiline: set[str], end_line: int) -> None:
        """Store the parsed fields."""
        self.fields = fields
        self.multiline = multiline
        self.end_line = end_line

    @classmethod
    def parse(cls, text: str) -> Frontmatter | None:
        """Parse the block between the opening and closing `---`, or return None when absent."""
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return None
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            return None
        fields: dict[str, str] = {}
        multiline: set[str] = set()
        key: str | None = None
        for raw in lines[1:end]:
            if raw.startswith((" ", "\t")) and key is not None:
                fields[key] = f"{fields[key]}\n{raw.strip()}".strip()
                continue
            name, sep, value = raw.partition(":")
            if not sep:
                continue
            key = name.strip()
            value = value.strip()
            if value in {">", "|", ">-", "|-"}:
                multiline.add(key)
                value = ""
            fields[key] = value.strip("\"'")
        return cls(fields, multiline, end + 1)


def estimate_tokens(text: str) -> float:
    """Estimate tokens: 1.3 per Latin word, 3 per word containing Cyrillic."""
    return sum(3.0 if CYRILLIC_RE.search(word) else 1.3 for word in text.split())


def body_lines(text: str) -> list[tuple[int, str]]:
    """Return (line number, text) for lines outside frontmatter and fenced code."""
    lines = text.splitlines()
    front = Frontmatter.parse(text)
    start = front.end_line if front is not None else 0
    result: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(lines[start:], start=start + 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            result.append((number, line))
    return result


def check_prose(path: Path, rel: str, text: str, style: bool = True) -> list[Finding]:
    """Check semicolons per sentence, sentence length and links that must resolve."""
    findings: list[Finding] = []
    lines = body_lines(text)
    for number, line in lines:
        if not style or line.lstrip().startswith("|"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", INLINE_CODE_RE.sub("", line)):
            if sentence.count(";") > MAX_SEMICOLONS:
                findings.append(
                    Finding(rel, number, "ERROR", "semicolons", "more than two in one sentence")
                )
            if len(sentence.split()) > LONG_SENTENCE_WORDS:
                findings.append(
                    Finding(rel, number, "WARN", "long-sentence", "over 40 words, split it")
                )
    # `references/x.md` names a file from the skill's root, wherever it is written.
    skill_root = path.parent.parent if path.parent.name == "references" else path.parent
    for number, raw in lines:
        links = LINK_RE.findall(INLINE_CODE_RE.sub("", raw))
        targets = [(path.parent, t) for t in links if not t.startswith(EXTERNAL_PREFIXES)]
        targets += [(skill_root, t) for t in REFERENCE_PATH_RE.findall(raw)]
        for base, target in targets:
            if not (base / target.split("#", 1)[0]).exists():
                findings.append(Finding(rel, number, "ERROR", "link", f"{target} does not exist"))
    return findings


def check_skill(skill_md: Path, root: Path) -> list[Finding]:
    """Check one SKILL.md and the reference files beside it."""
    rel = skill_md.relative_to(root).as_posix()
    text = read(skill_md)
    findings: list[Finding] = []
    front = Frontmatter.parse(text)
    if front is None:
        return [Finding(rel, 1, "ERROR", "frontmatter", "missing or unterminated frontmatter")]
    name = front.fields.get("name", "")
    folder = skill_md.parent.name
    if name != folder or not NAME_RE.match(name):
        findings.append(
            Finding(rel, 2, "ERROR", "name", f"'{name}' must equal the folder '{folder}'")
        )
    description = front.fields.get("description", "")
    if not description:
        findings.append(Finding(rel, 1, "ERROR", "description", "missing description"))
    user_only = front.fields.get("disable-model-invocation", "").lower() == "true"
    if user_only:
        if "description" in front.multiline and "\n" in description:
            findings.append(
                Finding(rel, 1, "ERROR", "description", "a user-invoked skill takes one line")
            )
    elif estimate_tokens(description) > DESCRIPTION_TOKEN_LIMIT:
        findings.append(
            Finding(rel, 1, "ERROR", "description", f"over {DESCRIPTION_TOKEN_LIMIT} tokens")
        )
    findings += check_model_and_effort(rel, front.fields)
    ported = folder in PORTED
    line_count = len(text.splitlines())
    if line_count > SKILL_LINE_LIMIT and not ported:
        findings.append(
            Finding(rel, line_count, "ERROR", "length", f"over {SKILL_LINE_LIMIT} lines")
        )
    findings += check_prose(skill_md, rel, text, style=not ported)
    for reference in sorted((skill_md.parent / "references").glob("*.md")):
        ref_rel = reference.relative_to(root).as_posix()
        ref_text = read(reference)
        ref_lines = len(ref_text.splitlines())
        if ref_lines > REFERENCE_LINE_LIMIT and not ported:
            findings.append(
                Finding(ref_rel, ref_lines, "ERROR", "length", f"over {REFERENCE_LINE_LIMIT} lines")
            )
        findings += check_prose(reference, ref_rel, ref_text, style=not ported)
    return findings


def check_model_and_effort(rel: str, fields: dict[str, str]) -> list[Finding]:
    """Check the optional `model` and `effort` fields shared by skills and agents."""
    findings: list[Finding] = []
    model = fields.get("model", "")
    if model and model not in MODELS and not model.startswith("claude-"):
        findings.append(Finding(rel, 1, "ERROR", "model", f"unknown model '{model}'"))
    effort = fields.get("effort", "")
    if effort and effort not in EFFORTS and not effort.isdigit():
        findings.append(Finding(rel, 1, "ERROR", "effort", f"unknown effort '{effort}'"))
    return findings


def check_agent(agent_md: Path, root: Path) -> list[Finding]:
    """Check one agent definition's frontmatter."""
    rel = agent_md.relative_to(root).as_posix()
    front = Frontmatter.parse(read(agent_md))
    if front is None:
        return [Finding(rel, 1, "ERROR", "frontmatter", "missing or unterminated frontmatter")]
    findings: list[Finding] = []
    fields = front.fields
    if fields.get("name") != agent_md.stem:
        findings.append(
            Finding(rel, 2, "ERROR", "name", f"name must equal the file name '{agent_md.stem}'")
        )
    if len(fields.get("description", "").split()) > AGENT_DESCRIPTION_WORDS:
        findings.append(
            Finding(rel, 1, "WARN", "description", f"over {AGENT_DESCRIPTION_WORDS} words")
        )
    findings += check_model_and_effort(rel, fields)
    turns = fields.get("maxTurns", "")
    if turns and (not turns.isdigit() or int(turns) < 1):
        findings.append(Finding(rel, 1, "ERROR", "maxTurns", "must be a positive integer"))
    return findings


def check_registry(root: Path) -> list[Finding]:
    """Every skill appears in the navigator's skill map, and the map names only real skills.

    No navigator (`skills/next`), no registry: a plugin without one is not checked here.
    """
    navigator = root / "skills" / "next" / "SKILL.md"
    if not navigator.is_file():
        return []
    text = read(navigator)
    section = text.split("## Skill map", 1)[1] if "## Skill map" in text else ""
    listed = set()
    for line in section.splitlines():
        if line.startswith("|"):
            cells = line.split("|")
            if len(cells) > 2:
                listed |= set(re.findall(r"`([a-z0-9-]+)`", cells[2]))
    skills = {p.parent.name for p in root.glob("skills/*/SKILL.md")} - {"next"}
    rel = navigator.relative_to(root).as_posix()
    found = [
        Finding(rel, 1, "ERROR", "registry", f"skill '{name}' is missing from the skill map")
        for name in sorted(skills - listed)
    ]
    found += [
        Finding(rel, 1, "ERROR", "registry", f"the skill map names '{name}', which does not exist")
        for name in sorted(listed - skills)
    ]
    return found


def check(root: Path) -> list[Finding]:
    """Check every skill and agent under the plugin root."""
    findings: list[Finding] = check_registry(root)
    for skill_md in sorted(root.glob("skills/*/SKILL.md")):
        findings += check_skill(skill_md, root)
    for agent_md in sorted(root.glob("agents/*.md")):
        findings += check_agent(agent_md, root)
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run the checks and return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        print(f"skillcheck: plugin root not found: {args.root}", file=sys.stderr)
        return 2
    if not (args.root / ".claude-plugin" / "plugin.json").is_file():
        print(
            f"skillcheck: {args.root} has no .claude-plugin/plugin.json: pass the plugin's own "
            "folder, or nothing would be checked",
            file=sys.stderr,
        )
        return 2
    try:
        findings = check(args.root)
    except CheckError as error:
        print(f"skillcheck: {error}", file=sys.stderr)
        return 2
    for finding in findings:
        print(finding.render())
    failing = {"ERROR", "WARN"} if args.strict else {"ERROR"}
    return 1 if any(f.level in failing for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
