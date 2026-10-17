import subprocess
from pathlib import Path

import pytest
from bedrock_lib import kb

DECISION = """---
type: decision
code: ACME-D1
status: {status}
date: 2026-10-01
decided_by: owner
tags: [decision]
parent: "[[decisions]]"
updated: 2026-10-01
---
# ACME-D1. Chunk size

## Decision
512 tokens.

## Why
Measured on the eval set (evals/chunks.md:12).

## Rejected
1024: recall dropped.

## Consequences
More chunks.

## Does not cancel
Nothing.

## Risk accepted
Slightly higher cost.
"""


INDEX = '---\ntype: index\ntags: [index]\nparent: "[[entry]]"\nupdated: 2026-10-17\n---\n'
MODULE_HEAD = (
    '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\n'
    "updated: 2026-10-17\ncovers: [src/ingest]\nanchors: []\nverified_at: abc\n---\n"
)
RUNBOOK_HEAD = '---\ntype: runbook\ntags: [runbook]\nparent: "[[runbooks]]"\n'


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def bank(tmp_path: Path) -> Path:
    root = tmp_path / "bank"
    kb.init(root, "Acme", "ACME", today="2026-10-17")
    return root


def problems(bank: Path, today: str = "2026-10-17") -> list[str]:
    return [p.message for p in kb.validate(bank, "Acme", today=today)]


def test_init_creates_a_valid_minimal_project(bank: Path) -> None:
    folder = bank / "Acme"
    for name in (
        "entry",
        "summary",
        "status",
        "architecture",
        "decisions",
        "failures",
        "runbooks",
        "handoffs",
        "open-questions",
    ):
        assert (folder / f"{name}.md").exists(), name
    assert (bank / ".git").exists()
    assert problems(bank) == []


def test_frontmatter_is_parsed() -> None:
    note = kb.parse(
        "x", '---\ntype: module\ncovers: [src/a, src/b]\nparent: "[[architecture]]"\n---\n# X\n'
    )
    assert note.meta["covers"] == ["src/a", "src/b"]
    assert note.meta["parent"] == "[[architecture]]"
    assert note.links == ["architecture"]


def test_broken_link_is_found(bank: Path) -> None:
    write(
        bank / "Acme",
        "decisions",
        INDEX + "# Decisions\n- [[ACME-D9]]\n",
    )
    assert any("ACME-D9" in m and "broken link" in m for m in problems(bank))


def test_missing_fields_and_headings(bank: Path) -> None:
    write(
        bank / "Acme" / "decisions",
        "ACME-D1",
        "---\ntype: decision\ncode: ACME-D1\n---\n# ACME-D1\n## Decision\nx\n",
    )
    found = " ".join(problems(bank))
    assert "missing field 'status'" in found
    assert "missing heading 'Why'" in found


def test_decision_code_needs_the_project_prefix(bank: Path) -> None:
    text = DECISION.format(status="accepted").replace("ACME-D1", "D1")
    write(bank / "Acme" / "decisions", "D1", text)
    assert any("project prefix" in m for m in problems(bank))


def test_edit_history_in_the_body_is_flagged(bank: Path) -> None:
    text = DECISION.format(status="accepted").replace(
        "512 tokens.", "512 tokens (previously 1024, updated on 2026-10-05)."
    )
    write(bank / "Acme" / "decisions", "ACME-D1", text)
    assert any("edit history" in m for m in problems(bank))


def test_superseded_decision_linked_as_current(bank: Path) -> None:
    write(bank / "Acme" / "decisions", "ACME-D1", DECISION.format(status="superseded"))
    body = "# Ingest\n## Purpose\nx\n## Boundaries\nx\n## Rules\nChunks follow [[ACME-D1]].\n"
    module = MODULE_HEAD + body + "## Pitfalls\nx\n"
    write(bank / "Acme" / "architecture", "ingest", module)
    assert any("superseded" in m and "ACME-D1" in m for m in problems(bank))


def test_orphan_and_long_notes(bank: Path) -> None:
    write(
        bank / "Acme" / "runbooks",
        "deploy",
        RUNBOOK_HEAD
        + "updated: 2026-10-17\nverified: 2026-10-17\n---\n# Deploy\n## Steps\n"
        + "x\n" * 310
        + "## Check it worked\n## Traps\n",
    )
    found = " ".join(problems(bank))
    assert "orphan" in found
    assert "over 300 lines" in found


def test_runbook_older_than_thirty_days_needs_reverification(bank: Path) -> None:
    write(
        bank / "Acme" / "runbooks",
        "deploy",
        RUNBOOK_HEAD
        + "updated: 2026-09-01\nverified: 2026-09-01\n---\n"
        + "# Deploy\n## Steps\n## Check it worked\n## Traps\n",
    )
    write(
        bank / "Acme",
        "runbooks",
        INDEX + "# Runbooks\n- [[deploy]]\n",
    )
    assert any("re-verify" in m for m in problems(bank))
    assert not any("re-verify" in m for m in problems(bank, today="2026-09-20"))


def sh(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def code(tmp_path: Path) -> Path:
    repo = tmp_path / "code"
    (repo / "src" / "ingest").mkdir(parents=True)
    (repo / "src" / "search").mkdir(parents=True)
    sh(repo, "init", "-q")
    sh(repo, "config", "user.email", "t@example.com")
    sh(repo, "config", "user.name", "t")
    (repo / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 1\n\n\ndef join():\n    return 2\n"
    )
    (repo / "src" / "search" / "find.py").write_text("x = 1\n")
    sh(repo, "add", ".")
    sh(repo, "commit", "-qm", "chore: start")
    return repo


def module_note(bank: Path, commit: str, anchors: str = "[]") -> None:
    text = (
        '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\nupdated: 2026-10-17\n'
        f"covers: [src/ingest]\nanchors: {anchors}\nverified_at: {commit}\n---\n# Ingest\n"
        "## Purpose\nx\n## Boundaries\nx\n## Rules\nx\n## Pitfalls\nx\n"
    )
    write(bank / "Acme" / "architecture", "ingest", text)


def test_drift_lists_notes_whose_code_changed(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert kb.drift(bank, "Acme", code) == []
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 2\n"
    )
    sh(code, "commit", "-qam", "fix: x")
    found = kb.drift(bank, "Acme", code)
    assert len(found) == 1
    assert "ingest" in found[0] and "src/ingest/chunk.py" in found[0]


def test_drift_with_anchors_counts_only_the_anchored_symbols(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 2\n"
    )
    sh(code, "commit", "-qam", "fix: x")
    assert kb.drift(bank, "Acme", code) == []
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 9\n"
    )
    sh(code, "commit", "-qam", "fix: y")
    assert len(kb.drift(bank, "Acme", code)) == 1


def test_drift_with_an_unknown_commit_says_so(bank: Path, code: Path) -> None:
    module_note(bank, "deadbeef")
    assert "unknown commit" in kb.drift(bank, "Acme", code)[0]


def test_module_without_a_note_is_flagged(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert kb.uncovered(bank, "Acme", code, ["src"]) == ["src/search"]


def test_backlinks(bank: Path) -> None:
    assert "entry" in kb.backlinks(bank, "Acme", "status")


def test_notes_covering_changed_files(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert [n.name for n in kb.covering(bank, "Acme", ["src/ingest/chunk.py"])] == ["ingest"]
    assert kb.covering(bank, "Acme", ["src/search/find.py"]) == []


def test_hidden_folders_are_not_modules(bank: Path, code: Path) -> None:
    (code / ".github").mkdir()
    assert kb.uncovered(bank, "Acme", code, ["."]) == ["src"]
