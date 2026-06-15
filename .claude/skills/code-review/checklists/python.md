# Python Checklist

Django, FastAPI, Flask, and the broader Python ecosystem.

## Language traps

- **Mutable default arguments:** `def f(x, items=[])` — `items` is shared across calls. Causes data leaks between requests if used in handlers. Always.
- **Late binding closures:** `[lambda: i for i in range(3)]` all return 2. Capture explicitly: `lambda i=i: i`.
- **`is` vs `==`:** `is` compares identity, not value. `if x is "string"` works sometimes (interning), fails sometimes — flag.
- **Bare `except:`** catches `KeyboardInterrupt`, `SystemExit`. Use `except Exception` at minimum, specific exceptions ideally.
- **`assert` for security checks:** Python with `-O` strips assertions. Never use `assert` for auth/validation in code paths that might run with optimizations.

## Framework-agnostic security

- `pickle.loads`, `marshal.loads`, `shelve.open` on untrusted data — RCE. See injection-deep.md.
- `yaml.load(x)` without `Loader=SafeLoader` — RCE. Use `yaml.safe_load`.
- `eval`, `exec`, `compile` on user input — flag instantly.
- `subprocess.run(..., shell=True)` with any user-derived input — command injection.
- `tempfile.mktemp` — race condition (TOCTOU). Use `tempfile.NamedTemporaryFile` / `mkstemp`.
- `random` module for security (tokens, passwords) — not cryptographic. Use `secrets`.

## Django

### Settings
- `DEBUG = True` in any settings module loaded in prod paths → CRITICAL.
- `ALLOWED_HOSTS = ['*']` or missing → host header attacks.
- `SECRET_KEY` hardcoded in settings.py committed to git → CRITICAL (token forgery).
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` not set in prod → MEDIUM.
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` missing in prod settings.
- Disabled middleware: missing `SecurityMiddleware`, `CsrfViewMiddleware`, `XFrameOptionsMiddleware`.

### ORM
- `.raw()` and `cursor.execute()` with f-string / format — SQL injection.
- `.extra(where=[...])` with user input — same.
- `Model.objects.get(id=request.GET['id'])` without ownership check → IDOR.
- `Model.objects.update(**request.POST)` — mass assignment.
- `select_for_update()` missing where row-level locking matters.

### Views
- Function views with no `@require_POST` / `@require_http_methods` — CSRF gaps.
- `@csrf_exempt` — every occurrence questioned.
- `request.user.is_authenticated` checked but `request.user.has_perm` not — auth without authz.
- Class-based views: `get_queryset` not filtering by user → all-tenant leak.
- `HttpResponseRedirect(request.GET.get('next'))` → open redirect.

### Templates
- `{% autoescape off %}` blocks — XSS surface.
- `|safe` filter on anything user-derived — XSS.
- Custom template tags that don't escape — audit each.

### Forms / DRF Serializers
- `ModelForm` / `ModelSerializer` with `fields = '__all__'` → mass assignment. Use explicit lists.
- Missing validators on email/url/integer fields where business logic assumes them.
- `read_only_fields` not used for `id`, `created_at`, `user` etc.

## FastAPI

### Dependency injection / auth
- `Depends(get_current_user)` not applied to protected routes — easy to forget on new endpoints.
- Dependency overrides in tests leaking to prod — flag if seen.
- Missing `response_model` → can leak fields not meant to be public.
- Returning Pydantic models that include sensitive fields → ensure `Config.exclude` or use a separate response model.

### Pydantic
- v1 vs v2 behavior differences — `Config` class vs `model_config`. Look for mixed usage.
- `Config: extra = "allow"` — accepts unknown fields → mass assignment risk.
- `validator` running side effects (DB calls) → don't.
- Pydantic v1 + `parse_obj_as` on untrusted input → check for known DoS via deep nesting.

### Async
- `async def` route handler calling `requests.get(...)` → blocks event loop. Use `httpx.AsyncClient`.
- `time.sleep` in async handler → same. Use `await asyncio.sleep`.
- DB driver mismatch: `psycopg2` (sync) in async handler → use `asyncpg` or `psycopg[async]`.
- Missing connection pooling in async DB usage → connection storm.

### Background tasks
- `BackgroundTasks` for anything user-facing that needs reliability — they run in-process, lost on crash. Use a real queue (Celery, RQ, Arq, dramatiq).

## Flask

### Routing / sessions
- `app.secret_key` hardcoded or weak → session forgery.
- `session` used without `SECURE`/`HTTPONLY`/`SAMESITE` cookie flags.
- `app.run(debug=True)` reachable in prod → CRITICAL (Werkzeug debugger = RCE).
- `app.config['DEBUG'] = True` via env var that might be set in prod.

### Extensions
- Flask-WTF: `WTF_CSRF_ENABLED = False` → CSRF missing.
- Flask-SQLAlchemy: `db.session.execute(text(f"..."))` with f-string → SQLi.
- Flask-Login: `@login_required` missing on protected routes.

### Jinja2
- `render_template_string(user_input)` → SSTI → RCE. CRITICAL.
- `Markup(user_input)` → XSS.
- `|safe` filter on user-derived content.

## SQLAlchemy

- `text(f"SELECT ... {x}")` with f-string — SQL injection.
- `session.execute(query)` then `for row in result: another_query(row.id)` → N+1.
- Missing `lazy='joined'` or `joinedload` / `selectinload` in hot relations → N+1.
- Detached instances accessed after session close → silent errors.
- Long-running session/transaction spanning a request → connection hoarding.

## Pip / supply chain

- `requirements.txt` without pinned versions or hashes → reproducibility + supply chain risk.
- `pip install` from arbitrary URLs in scripts.
- `setup.py` `install_requires` with very broad ranges.
- Packages installed from forks / unofficial mirrors.

## Logging

- `logging.exception` good; `logging.error(str(e))` loses stack. Prefer the former.
- `print()` in production code paths (vs proper logger) — flag.
- `logger.info(f"User {user} logged in: {request.headers}")` — logs auth tokens / cookies. PII leak.
- `LOGGING` configured to send to a file in a non-rotating manner → disk fill.

## Common bad patterns

```python
# TOCTOU
if not os.path.exists(path):
    open(path, "w").write(data)  # another process can create it in between
# Fix: open with O_CREAT | O_EXCL, or just write and handle FileExistsError

# Catching everything, logging nothing
try:
    do_thing()
except:
    pass  # flag

# Float for money
price = 9.99
total = price * 100  # 999.0000000000001
# Fix: Decimal

# datetime without tz
created = datetime.now()  # naive, depends on server TZ
# Fix: datetime.now(timezone.utc)

# Iterating QuerySet multiple times
qs = Model.objects.filter(...)
count = qs.count()       # one query
for x in qs: ...         # another query
# Fix: list(qs) once if you need both, or design to need only one
```
