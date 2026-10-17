import json
import subprocess
from pathlib import Path

import pytest
from bedrock_lib import codecheck, packages


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    (root / "README.md").write_text("x\n")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "chore: start")
    return root


def stage(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", "-A")


def commit(repo: Path, files: dict[str, str]) -> None:
    stage(repo, files)
    git(repo, "commit", "-q", "-m", "chore: base")


def checks(repo: Path, **options: object) -> list[str]:
    return [f.check for f in codecheck.run_checks(repo, network=False, **options)]


PATCH = 'from unittest import mock\n@mock.patch("{target}")\ndef test(): ...\n'


def function(name: str, body_lines: int) -> str:
    return f"def {name}() -> None:\n" + "    x = 1\n" * body_lines


def test_clean_change_passes(repo: Path) -> None:
    stage(repo, {"app/search.py": "def find(q: str) -> str:\n    return q\n"})
    assert codecheck.run_checks(repo, network=False) == []


def test_new_file_over_the_size_limit(repo: Path) -> None:
    stage(repo, {"app/big.py": "x = 1\n" * 401})
    assert checks(repo) == ["size"]


def test_existing_oversized_file_may_not_grow_but_may_shrink(repo: Path) -> None:
    commit(repo, {"app/big.py": "x = 1\n" * 500})
    stage(repo, {"app/big.py": "x = 1\n" * 499})
    assert checks(repo) == []
    stage(repo, {"app/big.py": "x = 1\n" * 501})
    assert checks(repo) == ["size"]


def test_function_size_ratchet(repo: Path) -> None:
    stage(repo, {"app/a.py": function("small", 59) + "\n\n" + function("huge", 61)})
    found = codecheck.run_checks(repo, network=False)
    assert [(f.check, f.line) for f in found] == [("size", 63)]
    git(repo, "commit", "-q", "-m", "chore: base")
    stage(repo, {"app/a.py": function("small", 59) + "\n\n" + function("huge", 62)})
    assert checks(repo) == ["size"]


@pytest.mark.parametrize(
    "name", ["app/utils.py", "src/helpers/index.ts", "lib/misc.js", "common/x.py"]
)
def test_dump_names(repo: Path, name: str) -> None:
    stage(repo, {name: "x = 1\n"})
    assert checks(repo) == ["dump name"]


def test_type_escape_needs_a_fixme(repo: Path) -> None:
    stage(repo, {"app/a.py": "x = f()  # type: ignore\n", "web/a.ts": "const y = z as any;\n"})
    assert checks(repo) == ["type escape", "type escape"]
    stage(
        repo,
        {
            "app/a.py": "x = f()  # type: ignore  # FIXME(lib has no stubs)\n",
            "web/a.ts": "// FIXME(api types missing)\nconst y = z as any;\n",
        },
    )
    assert checks(repo) == []


def test_removed_assertion_new_skip_and_deleted_test_file(repo: Path) -> None:
    commit(
        repo,
        {
            "tests/test_a.py": "def test_a():\n    assert f() == 1\n    assert g() == 2\n",
            "tests/test_b.py": "def test_b():\n    assert True\n",
            "web/a.test.ts": "it('works', () => { expect(f()).toBe(1) })\n",
        },
    )
    (repo / "tests" / "test_b.py").unlink()
    stage(
        repo,
        {
            "tests/test_a.py": "def test_a():\n    assert f() == 1\n",
            "web/a.test.ts": "it.skip('works', () => { expect(f()).toBe(1) })\n",
        },
    )
    found = codecheck.run_checks(repo, network=False)
    assert sorted((f.path, f.message.split(":")[0]) for f in found) == [
        ("tests/test_a.py", "assertion removed"),
        ("tests/test_b.py", "test file deleted"),
        ("web/a.test.ts", "skip or only added"),
    ]
    assert checks(repo, allow_test_changes=True) == []


def test_adding_tests_is_not_tampering(repo: Path) -> None:
    stage(repo, {"tests/test_new.py": "def test_new():\n    assert 1 == 1\n"})
    assert checks(repo) == []


def test_mock_of_internal_module(repo: Path) -> None:
    commit(repo, {"app/__init__.py": "", "app/search.py": "def find(): ...\n"})
    stage(
        repo,
        {
            "tests/test_s.py": PATCH.format(target="app.search.find"),
            "web/s.test.ts": "jest.mock('./search')\n",
        },
    )
    assert checks(repo) == ["internal mock", "internal mock"]


def test_mock_of_an_external_boundary_is_fine(repo: Path) -> None:
    commit(repo, {"app/__init__.py": ""})
    stage(
        repo,
        {
            "tests/test_s.py": PATCH.format(target="requests.get"),
            "web/s.test.ts": "jest.mock('axios')\n",
        },
    )
    assert checks(repo) == []


@pytest.mark.parametrize(
    ("line", "flagged"),
    [
        ('API = "https://api.acme-corp.io/v2"', True),
        ('host = "10.0.4.17"', True),
        ('ns = "http://www.w3.org/2000/svg"', False),
        ('url = os.environ["API_URL"]', False),
        ('doc = "https://example.com/x"', False),
    ],
)
def test_hardcoded_config_in_source(repo: Path, line: str, flagged: bool) -> None:
    stage(repo, {"app/client.py": line + "\n"})
    assert ("hardcoded config" in checks(repo)) is flagged


def test_urls_in_config_docs_and_tests_are_fine(repo: Path) -> None:
    line = 'API = "https://api.acme-corp.io/v2"\n'
    stage(repo, {"config/settings.yaml": line, "docs/a.md": line, "tests/test_c.py": line})
    assert checks(repo) == []


@pytest.mark.parametrize(
    ("line", "flagged"),
    [
        ('cur.execute(f"SELECT * FROM users WHERE id = {uid}")', True),
        ("db.query(`DELETE FROM t WHERE id = ${id}`)", True),
        ('q = "UPDATE t SET a = " + value', True),
        ('cur.execute("SELECT * FROM users WHERE id = %s", (uid,))', False),
        ('label = f"Select a file: {name}"', False),
    ],
)
def test_raw_sql_built_from_strings(repo: Path, line: str, flagged: bool) -> None:
    stage(repo, {"app/repo.py": line + "\n"})
    assert ("raw sql" in checks(repo)) is flagged


@pytest.mark.parametrize(
    "line", ["console.log(user)", "debugger;", "breakpoint()", "import pdb; pdb.set_trace()"]
)
def test_debug_leftovers(repo: Path, line: str) -> None:
    name = "web/a.ts" if line[0] in "cd" else "app/a.py"
    stage(repo, {name: line + "\n"})
    assert checks(repo) == ["debug leftover"]


@pytest.mark.parametrize(
    ("message", "ok"),
    [
        ("feat(search): dedupe results", True),
        ("fix: handle empty query", True),
        ("Fix bug", False),
        ("feature(search): x", False),
        ("feat(search): x\n\nbody text", False),
        ("feat(search): " + "x" * 80, False),
        ("feat(search):  ", False),
    ],
)
def test_commit_message_format(message: str, ok: bool) -> None:
    assert (codecheck.check_message(message) == []) is ok


def test_new_dependencies_are_found_in_manifests(repo: Path) -> None:
    commit(repo, {"package.json": json.dumps({"dependencies": {"react": "18.3.1"}}, indent=1)})
    manifest = {
        "dependencies": {"react": "18.3.1", "lodahs": "4.0.0"},
        "devDependencies": {"vitest": "2.1.0"},
    }
    stage(
        repo,
        {
            "package.json": json.dumps(manifest, indent=1),
            "requirements.txt": "requests==2.32.3\nreqeusts>=1\n# comment\n",
        },
    )
    added = packages.added_dependencies(codecheck.changes(repo))
    assert sorted(added) == [
        ("npm", "lodahs"),
        ("npm", "vitest"),
        ("pypi", "reqeusts"),
        ("pypi", "requests"),
    ]


def test_package_existence_uses_the_registry_answer() -> None:
    now = 1_792_000_000.0

    def fetch(url: str) -> dict | None:
        if url.endswith("/lodahs"):
            return None
        if "downloads" in url:
            return {"downloads": 50 if "fresh-pkg" in url else 5_000_000}
        if url.endswith("/fresh-pkg"):
            return {"time": {"created": "2026-10-01T00:00:00.000Z"}}
        return {"time": {"created": "2015-01-01T00:00:00.000Z"}}

    found = packages.check([("npm", "lodahs"), ("npm", "fresh-pkg"), ("npm", "react")], fetch, now)
    assert [(label, message.split(":")[0]) for label, message in found] == [
        ("npm:lodahs", "not in the registry"),
        ("npm:fresh-pkg", "younger than 90 days"),
        ("npm:fresh-pkg", "under 1000 downloads a week"),
    ]


def test_registry_unreachable_cannot_verify() -> None:
    def fetch(url: str) -> dict | None:
        raise OSError("offline")

    with pytest.raises(packages.RegistryError):
        packages.check([("pypi", "requests")], fetch, 0.0)


def test_type_escape_patterns_follow_the_language(repo: Path) -> None:
    stage(
        repo,
        {
            "app/a.py": '"""It never fails: any error still prints a line."""\n',
            "web/b.ts": "// It never fails: any error\nlet v: any = 1;\n",
        },
    )
    assert [(f.path, f.line) for f in codecheck.run_checks(repo, network=False)] == [
        ("web/b.ts", 2)
    ]


def test_allowed_hosts_are_not_hardcoded_config(repo: Path) -> None:
    stage(repo, {"app/reg.py": 'meta = fetch(f"https://registry.npmjs.org/{name}")\n'})
    assert checks(repo) == ["hardcoded config"]
    assert checks(repo, allow_hosts=("registry.npmjs.org",)) == []


def test_weakened_assertion_is_flagged(repo: Path) -> None:
    commit(repo, {"tests/test_a.py": "def test_a():\n    assert f() == 1\n"})
    stage(repo, {"tests/test_a.py": "def test_a():\n    assert f() == 1 or True\n"})
    assert checks(repo) == ["test tampering"]


def test_failed_downloads_lookup_does_not_block_a_verified_package() -> None:
    import urllib.error

    def fetch(url: str) -> dict | None:
        if "pypistats" in url or "api.npmjs.org" in url:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        if "pypi.org" in url:
            item = {"upload_time_iso_8601": "2015-01-01T00:00:00Z"}
            return {"releases": {"1.0": [item]}}
        return {"time": {"created": "2015-01-01T00:00:00.000Z"}}

    assert packages.check([("pypi", "requests"), ("npm", "react")], fetch, 1_792_000_000.0) == []


@pytest.mark.parametrize("line", ['HOST = "127.0.0.1"', 'BIND = "0.0.0.0"', 'LOOP = "127.0.0.53"'])
def test_loopback_addresses_are_not_config(repo: Path, line: str) -> None:
    stage(repo, {"app/net.py": line + "\n"})
    assert checks(repo) == []
