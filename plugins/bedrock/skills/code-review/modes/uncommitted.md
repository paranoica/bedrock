# Mode: Uncommitted Changes Review

Use when the user wants their current local work reviewed before committing.

## Setup

1. Verify we're in a git repo:
   ```bash
   git rev-parse --show-toplevel
   ```
   If not a git repo, tell the user and switch to full-project mode if they want.

2. Collect all uncommitted work — staged, unstaged, and untracked new files:
   ```bash
   # Staged
   git diff --cached --stat
   git diff --cached

   # Unstaged (modifications to tracked files)
   git diff --stat
   git diff

   # Untracked (new files not yet added)
   git ls-files --others --exclude-standard
   ```

3. If there's literally nothing uncommitted:
   ```bash
   git status --short
   ```
   Report this honestly: "Нечего ревьюить — рабочая директория чистая." Don't fabricate findings.

4. **Size check.** If the diff is huge (`git diff --cached --shortstat` + unstaged > ~2000 lines changed), tell the user:
   > Диф большой (X строк изменений). Я разделю на части по файлам/директориям. Если хочешь, сначала только staged, потом unstaged?

## Special case — untracked files

`git diff` won't show new files. Read them in full:
```bash
git ls-files --others --exclude-standard | while read f; do
  echo "=== $f ==="
  cat "$f"
done
```
Treat them as 100% additions for review purposes.

## Context awareness

For each modified file, also look at unchanged surrounding code:
- The function being modified — read the whole function, not just the diff hunk
- Functions called from the changed code — at least their signatures
- Type definitions / schemas referenced

This prevents the classic LLM-reviewer failure of flagging things that are already handled elsewhere.

```bash
# For each changed file, show full file alongside diff context
git diff --name-only HEAD | while read f; do
  echo "=== $f ==="
  wc -l "$f"
done
```

## Pass back to SKILL.md

Once the diff and surrounding context are gathered, return to SKILL.md "Universal workflow" Step 1.
