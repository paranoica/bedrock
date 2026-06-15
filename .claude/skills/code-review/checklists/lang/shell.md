# Shell / Bash — language module

Covers POSIX sh, Bash, and the shell embedded in CI YAML, Dockerfiles, entrypoints, and
provisioning scripts. High ROI because it lives everywhere and its injection surface is wide.
Built on `checklists/taint-spine.md`. Static helper: **ShellCheck** (cite SC codes); cross-ref
its output and drop FPs like any tool.

## Sinks by S-category

- **S3 Command / code injection** — the dominant class.
  - `eval "$user"` — arbitrary code; almost never justified.
  - Unquoted expansion in a command: `rm -rf $dir`, `cmd $args` — word-splitting + glob means
    `$dir="; rm -rf /"` or a path with spaces/globs changes the command. **Quote every
    expansion**: `"$dir"`, `"$@"` (never `$*`/`$@` unquoted).
  - User data in `bash -c "$str"`, `sh -c`, `ssh host "$cmd"`, `find … -exec sh -c '…' \;`.
  - Tainted data interpolated into `awk`/`sed`/`perl -e` programs.
- **S7 Path** — user-derived filenames in `cat`/`rm`/`>`/redirections without confinement;
  `../` traversal; a filename beginning with `-` parsed as a flag (use `-- "$f"` to terminate
  options).
- **S8/supply-chain** — `curl … | bash` / `wget -O - | sh` (executing un-pinned remote code),
  fetching over plain HTTP, no checksum/signature verification on a downloaded artifact.
- **S1** — building SQL strings passed to `psql -c "$q"` / `mysql -e` from input.

## Footguns (taint-independent)

- **No `set -euo pipefail`.** Without it, a failed command is ignored and the script charges on
  (e.g. `cd "$dir" && rm -rf .` — if `cd` fails, you delete the *current* dir). Unset variables
  expand to empty (`rm -rf "$PREFIX/"` with empty `PREFIX` → `rm -rf /`). Missing `pipefail`
  hides failures mid-pipe. Absence of these on a script that deletes/moves/deploys is a finding.
- **Word-splitting on command substitution** — `for f in $(ls)` breaks on spaces/newlines; use
  globs or `find -print0 | xargs -0` / `while IFS= read -r`.
- **`[ $x = y ]` unquoted** — empty/whitespace `$x` causes a syntax error or wrong branch; use
  `[ "$x" = y ]` or `[[ ]]`.
- **Tempfile races (TOCTOU)** — predictable `/tmp/$$` names; use `mktemp`.
- **Secrets on the command line** — visible in `ps`/process list and in `set -x` traces; passwords
  as args, or `set -x` left on while handling a token.
- **Parsing `ls`** output, or relying on `$IFS` defaults after modifying it.

## Sanitizer idioms (what "safe" looks like)

- Every variable expansion quoted; `"$@"` for arg passthrough; `--` before filename operands.
- No `eval` on data; build argument **arrays** (`cmd=(git log "$branch"); "${cmd[@]}"`) instead
  of string-built commands.
- `set -euo pipefail` at the top of any non-trivial script; explicit error handling on the few
  commands allowed to fail.
- Remote artifacts pinned + checksum/signature-verified before execution; never pipe-to-shell.
- `mktemp` for temp files; secrets passed via env/stdin/files, never argv, with `set +x` around them.

## Notes

A ShellCheck-clean script with `set -euo pipefail` and fully-quoted expansions clears most of
this. Severity per `references/severity-rubric.md`: `eval`/unquoted-in-destructive-command →
CRITICAL/HIGH; missing `set -e` on a deploy/delete script → HIGH; missing quotes with no
dangerous sink → MEDIUM/LOW.
