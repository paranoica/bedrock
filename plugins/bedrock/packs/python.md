# Pack: Python

## Rules
- Type hints on every public function; `mypy` or `pyright` in the project's typecheck command.
- No bare `except:`; catch the narrowest error and keep its cause (`raise … from error`).
- No mutable default arguments. No `eval`, `exec` or `pickle` on data from outside.
- Subprocesses get an argument list, never `shell=True` with built strings.
- Paths through `pathlib`; files opened with an explicit encoding.

## Critical zones to consider
Migrations, authentication, payment code, anything that deletes data.

## Reviewer checklist
- SQL built with parameters, not f-strings.
- Timeouts on every network call; retries with a cap.
- Resources closed (`with`), no file handles leaked in loops.
- Timezone-aware datetimes; UTC in storage.

## Test checklist
- pytest; properties with Hypothesis for parsers, money and date logic.
- Edges: empty, None, zero, max, one past max, unicode, the first and last item.
- No test passes by mocking the thing under test.
