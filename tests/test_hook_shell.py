import pytest
from bedrock_hooks import shell


def argvs(command: str) -> list[list[str]]:
    return [simple.argv for simple in shell.commands(command)]


def test_one_command() -> None:
    assert argvs("git status") == [["git", "status"]]


@pytest.mark.parametrize("joiner", ["&&", "||", ";", "|", "&", "\n"])
def test_compound_commands_are_split(joiner: str) -> None:
    assert argvs(f"cd app {joiner} git push") == [["cd", "app"], ["git", "push"]]


def test_subshell_and_groups() -> None:
    assert argvs("(cd x && git push) ; { git status; }") == [
        ["cd", "x"],
        ["git", "push"],
        ["git", "status"],
    ]


def test_redirections_are_dropped() -> None:
    assert argvs("git push 2>/dev/null >> log.txt 2>&1 < in") == [["git", "push"]]


@pytest.mark.parametrize(
    "prefix",
    [
        *("FOO=1 BAR=2", "sudo", "sudo -u root", "env", "env -i A=b", "command", "nohup"),
        *("time", "exec", "nice -n 5", "timeout 30", "timeout -s KILL 10s", "doas", "builtin"),
    ],
)
def test_prefixes_are_unwrapped(prefix: str) -> None:
    assert argvs(f"{prefix} git push") == [["git", "push"]]


@pytest.mark.parametrize(
    "command",
    [
        'bash -c "git push --force"',
        "sh -c 'git push --force'",
        'zsh -lc "cd x; git push --force"',
        'eval "git push --force"',
        "echo $(git push --force)",
        "echo `git push --force`",
        'x="$(git push --force)"',
    ],
)
def test_nested_commands_are_found(command: str) -> None:
    assert ["git", "push", "--force"] in argvs(command)


def test_xargs_runs_its_command() -> None:
    assert ["git", "branch", "-D"] in argvs("git branch | xargs git branch -D")


def test_quoted_newline_stays_inside_the_argument() -> None:
    assert argvs('git commit -m "subject\n\nbody"') == [["git", "commit", "-m", "subject\n\nbody"]]


def test_unbalanced_quotes_raise() -> None:
    with pytest.raises(shell.ParseError):
        shell.commands('git commit -m "oops')


def test_program_name_drops_the_path() -> None:
    assert shell.commands("/usr/bin/git push")[0].program == "git"


def test_empty_command() -> None:
    assert shell.commands("   ") == []


def test_xargs_options_before_the_command() -> None:
    assert ["rm", "-rf"] in argvs("find . -name x | xargs -n 1 -I {} rm -rf")


def test_find_exec_runs_its_command() -> None:
    assert ["git", "push", "--force"] in argvs(r"find . -maxdepth 0 -exec git push --force \;")


def test_redirect_targets_are_kept_aside() -> None:
    found = shell.commands("echo x > ~/.claude/settings.json 2>&1; cat a >> log.txt")
    assert [simple.redirects for simple in found] == [["~/.claude/settings.json"], ["log.txt"]]


def test_blank_lines_and_heredoc_bodies_split_commands() -> None:
    assert argvs("cat > notes.md <<'EOF'\nrun git push\nEOF\n\necho done") == [
        ["cat"],
        ["echo", "done"],
    ]
    assert argvs("a;\nb") == [["a"], ["b"]]


def test_glued_punctuation_still_separates() -> None:
    assert argvs("(cd /tmp); echo x") == [["cd", "/tmp"], ["echo", "x"]]
    assert argvs("a&&(b||c);d") == [["a"], ["b"], ["c"], ["d"]]
