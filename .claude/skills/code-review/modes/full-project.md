# Mode: Full Project Review

Use when the user wants the entire codebase audited.

## Setup

1. Confirm project root:
   ```bash
   pwd && ls -la
   ```
   If the user is in a subdirectory of a larger repo, ask whether to scope to the subdir or go up to the git root.

2. Get the lay of the land:
   ```bash
   # Source file count by language
   find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \
     -o -name "*.py" -o -name "*.sql" \) \
     -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/dist/*" \
     -not -path "*/build/*" -not -path "*/__pycache__/*" -not -path "*/.venv/*" \
     -not -path "*/venv/*" | wc -l

   # Lockfiles present
   ls -1 package.json pnpm-lock.yaml yarn.lock requirements.txt pyproject.toml \
     poetry.lock Pipfile go.mod 2>/dev/null

   # Entry points (rough)
   grep -rEl "(app\.(get|post|put|delete|patch)|@app\.route|@router\.(get|post)|FastAPI\(\)|express\(\))" \
     --include="*.py" --include="*.ts" --include="*.js" \
     --exclude-dir=node_modules --exclude-dir=.venv . 2>/dev/null | head -50
   ```

3. **Size check.** If source file count > 500, do not try to review everything in one pass. Tell the user:
   > Проект большой (N файлов). Я не смогу качественно проревьюить всё за один проход — контекст кончится и я начну халтурить. Предлагаю варианты:
   > 1. Сначала только то, что трогает untrusted input (роуты, обработчики, queue consumers)
   > 2. Только директория X
   > 3. Только изменения с последнего тега / последнего месяца
   > Что выбираешь?

   Wait for the answer before continuing.

## Prioritization

When reviewing a full project, walk files in this order — don't go alphabetically:

1. **Auth/session/permissions** — anything in `auth/`, `users/`, files matching `*permission*`, `*authoriz*`, `*session*`, `*token*`, `*jwt*`, `middleware/auth*`.
2. **HTTP/API handlers** — route files, controllers, FastAPI/Flask views, Next.js API routes (`app/api/`, `pages/api/`).
3. **Database access layer** — models, ORM definitions, raw query builders, migrations.
4. **External integrations** — anything that talks to third parties, especially with user-controlled input flowing in.
5. **Business logic** — services, domain code.
6. **Frontend** — only flag XSS, dangerous DOM access, exposed secrets in client bundles, leaky error handling.
7. **Config/infra** — `Dockerfile`, compose, CI configs (secrets, perms).
8. **Tests** — last, and only flag if they assert wrong things or hide bugs.

## Pass back to SKILL.md

Once the file list is prioritized and the user confirmed scope, return to SKILL.md "Universal workflow" Step 1.
