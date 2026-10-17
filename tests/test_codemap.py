import json
import subprocess
from pathlib import Path

import pytest
from bedrock_lib import codemap


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    (root / "api").mkdir(parents=True)
    (root / "web").mkdir()
    (root / "api" / "auth.py").write_text(
        "class AuthError(Exception):\n    pass\n\n\ndef verify_token(t):\n    return decode(t)\n"
    )
    (root / "api" / "views.py").write_text("def login(r):\n    return verify_token(r.token)\n")
    (root / "web" / "client.ts").write_text(
        "export function fetchUser(id: string) {\n  return request(id)\n}\n"
        "const render = (u) => paint(u)\n"
    )
    (root / "node_modules").mkdir()
    (root / "node_modules" / "x.js").write_text("function vendored() {}\n")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    (root / ".gitignore").write_text("node_modules/\n")
    return root


def test_build_maps_definitions_and_callers(repo: Path) -> None:
    data = codemap.build(repo)
    assert data["version"] == 1
    assert data["symbols"]["verify_token"] == ["api/auth.py"]
    assert data["callers"]["verify_token"] == ["api/views.py"]
    assert "AuthError" in data["files"]["api/auth.py"]["defs"]
    assert {"fetchUser", "render"} <= set(data["files"]["web/client.ts"]["defs"])
    assert "request" in data["files"]["web/client.ts"]["calls"]


def test_ignored_and_vendored_files_are_left_out(repo: Path) -> None:
    assert not any(path.startswith("node_modules") for path in codemap.build(repo)["files"])


def test_written_map_is_fresh_until_a_file_changes(repo: Path) -> None:
    target = codemap.store(repo.parent / "state", repo)
    assert codemap.check(repo, target) == "absent"
    codemap.write(target, codemap.build(repo))
    assert json.loads(target.read_text())["stamp"]["file_count"] == 3
    assert codemap.check(repo, target) == "fresh"
    assert not (repo / ".map").exists()
    (repo / "api" / "views.py").write_text("def login(r):\n    return None\n")
    assert codemap.check(repo, target) == "stale"


def test_new_file_makes_the_map_stale(repo: Path) -> None:
    target = codemap.store(repo.parent / "state", repo)
    codemap.write(target, codemap.build(repo))
    (repo / "api" / "new.py").write_text("x = 1\n")
    assert codemap.check(repo, target) == "stale"


def test_rebuild_reuses_unchanged_files(repo: Path) -> None:
    first = codemap.build(repo)
    first["files"]["api/auth.py"]["defs"].append("marker")
    second = codemap.build(repo, previous=first)
    assert "marker" in second["files"]["api/auth.py"]["defs"]


def test_python_that_does_not_parse_is_marked(repo: Path) -> None:
    (repo / "api" / "broken.py").write_text("def x(:\n")
    assert codemap.build(repo)["files"]["api/broken.py"]["lang"] == "py-parse-error"


def test_outside_git_the_tree_is_walked(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def f():\n    pass\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "b.py").write_text("def g():\n    pass\n")
    data = codemap.build(tmp_path)
    assert list(data["files"]) == ["a.py"]
    assert data["stamp"]["git_head"] is None


def test_old_or_partial_maps_are_rebuilt_not_trusted(repo: Path, tmp_path: Path) -> None:
    data = codemap.build(repo, previous={"version": 0, "files": {"api/auth.py": {"hash": "x"}}})
    assert "verify_token" in data["symbols"]
    target = tmp_path / "m.json"
    target.write_text('{"version": 0}')
    assert codemap.load(target) is None
    assert codemap.check(repo, target) == "absent"


def test_rust_go_and_java_definitions(tmp_path: Path) -> None:
    (tmp_path / "lib.rs").write_text(
        "pub fn parse() {}\npub struct Doc;\nimpl Doc {\n    pub fn len(&self) {}\n}\n"
    )
    (tmp_path / "svc.go").write_text("func (s *Svc) Handle() {}\nfunc main() {}\n")
    (tmp_path / "A.java").write_text("public class A {\n    public void run() {}\n}\n")
    files = codemap.build(tmp_path)["files"]
    assert {"parse", "Doc", "len"} <= set(files["lib.rs"]["defs"])
    assert {"Handle", "main"} <= set(files["svc.go"]["defs"])
    assert {"A", "run"} <= set(files["A.java"]["defs"])


def test_non_ascii_paths_are_mapped(repo: Path) -> None:
    (repo / "api" / "файл.py").write_text("def f():\n    pass\n")
    assert "api/файл.py" in codemap.build(repo)["files"]
