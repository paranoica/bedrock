# Mode: PR Review

Use when the user wants to review someone else's pull request on GitHub.

## Setup

1. Get the PR identifier from the user. Accept any of:
   - PR number (e.g., `#123` or `123`) — assumes we're in the right repo
   - Full GitHub URL: `https://github.com/owner/repo/pull/123`
   - `owner/repo#123` shorthand

2. Check `gh` CLI is available:
   ```bash
   gh --version
   ```
   If not installed: tell the user to install `gh` (`brew install gh` / `apt install gh`) and authenticate (`gh auth login`). Don't try to use the GitHub API raw with curl as a workaround — auth becomes a mess.

3. Fetch PR metadata + diff:
   ```bash
   # Metadata: title, description, author, base branch
   gh pr view <PR-REF> --json title,body,author,baseRefName,headRefName,additions,deletions,changedFiles,files

   # Full diff
   gh pr diff <PR-REF>
   ```

   If the PR is in a different repo than the current working directory, use `--repo owner/repo`:
   ```bash
   gh pr view 123 --repo someorg/somerepo --json ...
   ```

4. **Size check.** Look at `additions + deletions`. If > 1500 lines, warn the user:
   > PR большой (X строк). Ревью будет менее детальным — сосредоточусь на critical/high. Если хочешь deep dive — давай по файлам или по коммитам.

## Read the PR description

The PR body often contains the *intent*. Use it:
- "This PR adds rate limiting" — verify the rate limiting actually works and can't be bypassed.
- "Fixes SQL injection in /search" — verify the fix is complete and not just one occurrence.
- No description / "wip" / "fixes bug" — flag this as a process issue at the bottom of the report (LOW).

**Compare intent to reality.** If the PR claims to fix X but also modifies Y in a sketchy way — that scope creep is worth flagging.

## Checkout for deeper inspection (optional)

If the diff alone isn't enough — e.g., you need to see the full file with the change applied to trace data flow — checkout locally:
```bash
gh pr checkout <PR-REF>
```
This puts you on the PR's branch. After review, the user can `git checkout -` to go back. Mention this if you do it.

If checkout isn't possible (dirty working tree, etc.), work from the diff + `gh pr diff <PR> --patch` for full hunks.

## Reviewer context

For PR review, also check:
- Whose PR is it? `gh pr view --json author` — first-time contributor or core team member changes how paranoid you are (LOW context, but useful).
- Are CI checks passing? `gh pr checks <PR-REF>` — if tests are failing, mention it in the summary, don't try to be the test runner.
- Existing review comments: `gh pr view <PR-REF> --comments` — don't repeat what someone else already flagged.

## Pass back to SKILL.md

Once the diff and PR metadata are collected, return to SKILL.md "Universal workflow" Step 1.
