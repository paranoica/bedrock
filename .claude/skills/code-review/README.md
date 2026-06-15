# Code Review Skill для Claude Code — v2

Жёсткий ревью-агент: безопасность (с упором на инъекции), перформанс, отказоустойчивость,
конкурентность, миграции/совместимость, supply-chain и best practices. Три режима: весь
проект, незакоммиченные изменения, чужой PR.

## Как это проверяется (честно)

Раньше в README стояло «46/46 багов, 0 false positives». Это была непроверяемая цифра —
её убрали. Вместо неё есть **eval-харнесс** (`evals/`), который реально гоняется:

- `evals/run_evals.sh` — детерминированные регрессии без модели: парсеры локфайлов
  (pnpm v9 / yarn Berry должны парситься, а не возвращать пусто), и верификатор должен
  резать выдуманные находки и не резать настоящие. **Все три проходят** (`ALL REGRESSIONS PASSED`).
- `evals/score.py` — скоринг конкретного прогона ревью против размеченных фикстур:
  recall / false-positives / hallucinations. Это превращает «качество ревью» в
  воспроизводимый CI-гейт, а не в обещание. Корпус — **24 пары vuln/safe**, каждая
  нацелена в сигнатурный баг своего модуля (13 языков + 9 инфра-поверхностей);
  safe-двойник проверяет precision. Карта корпуса и idempotent-builder — в
  `evals/README.md` / `evals/build_fixtures.py`.

Запускай регрессии при каждом изменении чек-листов/промптов:

```bash
./evals/run_evals.sh
```

## Что нового в v2

**Исправленные баги v1 (все проверены прогоном):**
- `check_cves.py` молча возвращал `[]` для **pnpm v5/v9** и **yarn Berry** → ложное
  «уязвимостей нет». Парсеры переписаны, покрывают все актуальные форматы.
- Severity бралась из мёртвого `if ...: pass` и почти всегда выходила `UNKNOWN`. Теперь
  считается **из CVSS-вектора** (реальный расчёт base score 3.1).
- PyPI-имена не нормализовались (`Django` ≠ `django`) → дубли запросов. Теперь PEP 503.
- `MAX_DEPS` резал по порядку парсеров и мог выкинуть все Python-зависимости. Теперь
  **сбалансированный кап** + batch-запросы к OSV (`/v1/querybatch`).
- Workspace-пакеты (`apps/web`) больше не уезжают в OSV как `npm:web`.
- `run_static_analysis.sh`: невалидный флаг semgrep `--error-on-findings=false` убран;
  `CACHE_DIR` был мёртвой переменной — теперь **реальный кэш** на хэше инвентаря файлов;
  gitleaks сам выбирает `dir` vs legacy `detect --no-git`; добавлен **diff-скоупинг**.
- Хардкод русской строки пустого Improvements исправлен на язык пользователя.

**Новые механизмы:**
- **Operating discipline** в SKILL.md — рыть, не лениться, не оправдывать находки, не
  терять смысл и контекст при фиксах (по явному запросу).
- **Step 5c — заземление**: `scripts/verify_findings.py` детерминированно проверяет
  «квитанцию» каждой находки (существует ли файл, есть ли процитированный код на этих
  строках, реальный ли CVE-id) и режет галлюцинации до отчёта. Плюс self-consistency
  для low-confidence.
- **Сабагент-верификатор** (`subagents/finding-verifier.md`) — перепроверяет находки в
  свежем контексте, которого он не генерировал; гейтится по scope. Спавнится как Task-
  сабагент из бандл-файла — **ничего класть в `~/.claude/agents/` не нужно**.
- **Калиброванный rubric severity** (`references/severity-rubric.md`): Impact ×
  Reachability × Exploitability, и confidence как отдельная ось.

**Новые оси ревью (чек-листы):** `resilience.md`, `concurrency-and-data-integrity.md`,
`migrations-and-compat.md`, `supply-chain.md`, `llm-slop.md`.

## Что добавлено во второй заход (v2.1)

Закрыт почти весь отложенный список идей:
- **privacy-and-data-flow.md** — трассировка PII в логи/аналитику/третьи стороны,
  data residency, retention, полнота right-to-delete.
- **finops.md** — регрессии облачного счёта: cross-AZ/egress, polling, взрыв логов,
  storage без lifecycle, idle-биллинг в serverless.
- **architecture.md** — layering violations, циклы импортов, god-объекты, и
  **здоровье зависимостей помимо CVE** (мёртвые/deprecated/bus-factor-1).
- **test-quality.md** — diff-coverage, тесты-пустышки, мок-самого-себя, флейки;
  «закомментируй реализацию — тест всё ещё проходит?».
- **removed-defenses.md** — ревью *удалений* в диффе: вырезанный auth-чек, валидация,
  таймаут, транзакция, тест = находка, пока не доказано, что защита переехала.
- **grounded-perf** — severity/перф с реальными числами из репо (размеры таблиц из
  миграций, батчи из конфига), а не абстрактное «O(n²)».
- **version-aware** — детект версий рантайма/фреймворков, чтобы не флагать футганы,
  которых в этой версии нет, и ловить те, что есть.
- **counterfactual-проверка safe-вердиктов** (Step 5c·4b) — на каждое «безопасно из-за
  защиты» построить вход, который её обошёл бы, и проверить, что защита держит.
- **calibration.py** — Brier-трекинг: confidence→p(TP), запись исходов, калибровочная
  таблица. «High confidence» становится измеримым, а не рефлекторным.
- **change_risk.py** — риск-скор диффа (0–100) + флаги `too_big` / `mixed_concerns` /
  `risky_no_tests`; роутит внимание и ловит PR, которые слишком велики для надёжного ревью.

## Что внутри

```
code-review/
├── SKILL.md                          # роутер + философия + дисциплина + anti-hallucination
├── modes/                            # full-project / uncommitted / pr-review
├── checklists/
│   ├── injection-deep.md             # SQLi, XSS, SSRF, RCE, prototype pollution, ReDoS, zip-slip, XML-bombs, CSV
│   ├── security-general.md           # auth, crypto, IDOR, CSRF, secrets, A04/A08
│   ├── performance.md                # N+1, индексы, кэш, event loop
│   ├── resilience.md                 # ★ таймауты, ретраи+jitter, circuit breaking, partial failure
│   ├── concurrency-and-data-integrity.md  # ★ гонки, TOCTOU, идемпотентность, транзакции, деньги
│   ├── migrations-and-compat.md      # ★ blocking DDL, rolling deploy, backward-compat контрактов
│   ├── supply-chain.md               # ★ typosquat, postinstall, lockfile drift, лицензии
│   ├── llm-slop.md                   # ★ галлюцинированные API, copy-paste drift, тесты-пустышки
│   ├── privacy-and-data-flow.md      # ★ PII в логи/аналитику/3rd-party, residency, retention, erasure
│   ├── finops.md                     # ★ cost-регрессии: egress, polling, логи, serverless
│   ├── architecture.md               # ★ layering, циклы, god-объекты, dep-health помимо CVE
│   ├── test-quality.md               # ★ diff-coverage, тесты-пустышки, флейки
│   ├── removed-defenses.md           # ★ ревью удалений в диффе (вырезанные гарды)
│   ├── improvements.md               # upside pass
│   ├── javascript-typescript.md      # Node, Next, React
│   ├── python.md                     # Django, FastAPI, Flask, SQLAlchemy
│   └── sql-and-data.md               # PostgreSQL, Redis, миграции
├── scripts/
│   ├── preflight.sh                  # ★ проба окружения: тулзы, OSV, PoC-изоляция → mode
│   ├── run_static_analysis.sh        # semgrep + gitleaks + bandit + eslint (кэш, diff-scope)
│   ├── check_cves.py                 # OSV.dev: batch + CVSS severity + все локфайлы
│   ├── check_cves.sh                 # обёртка
│   ├── build_index.py                # ★ персистентный repo-граф (defs/calls, инкрементальный)
│   ├── poc_runner.sh                 # ★ запуск минимального PoC в песочнице (no-net, лимиты)
│   ├── verify_findings.py            # ★ детерминированное заземление находок
│   ├── record_outcome.py             # ★ исходы → suppressions + standards + калибровка
│   ├── change_risk.py                # ★ риск-скор диффа + too-big/mixed-concerns/no-tests
│   └── calibration.py                # ★ Brier-трекинг калибровки confidence
├── subagents/
│   └── finding-verifier.md           # ★ верификатор (спавнится как Task-сабагент, без install)
├── references/
│   ├── report-template.md            # формат отчёта
│   └── severity-rubric.md            # ★ калиброванная severity + confidence
└── evals/
    ├── run_evals.sh                  # ★ 10 детерминированных регрессий
    ├── score.py                      # ★ recall / precision / F1 / FP / hallucination scoring
    ├── expected.json                 # размеченные ожидания
    └── fixtures/                     # 24 vuln/safe пар (13 языков + 9 инфра) + локфайлы + находки + дифф-фикстуры

★ = новое в v2 / v2.1
```

## Установка

```bash
# Глобально:
mkdir -p ~/.claude/skills && cp -r code-review ~/.claude/skills/
# Или для одного проекта:
mkdir -p .claude/skills && cp -r code-review .claude/skills/
```

Сабагент-верификатор **не требует установки** — скилл спавнит его как Task-сабагент прямо из
`subagents/finding-verifier.md`. (При желании его можно зарегистрировать как именованный агент,
положив в `~/.claude/agents/`, но это необязательно.) Перезапусти сессию Claude Code.

## Зависимости (опциональные)

Скилл работает и без них — пропускает шаги и говорит, чего не хватает.

```bash
pip install semgrep bandit         # статанализ + Python security linter
brew install gitleaks jq           # секреты + агрегация JSON
brew install gh && gh auth login   # только для PR-режима
```

Python 3 и git — само собой. `verify_findings.py` и парсеры CVE — на чистом stdlib,
без зависимостей.

## Использование

- **«Сделай ревью проекта»** / «audit this codebase» → full-project
- **«Проверь мои изменения»** / «review uncommitted» → uncommitted (diff-scoped)
- **«Посмотри PR #123»** / URL на GitHub PR → pr-review (compat-чек включён по умолчанию)

Сработает и на «найди уязвимости», «есть ли тут SQLi», «оптимизируй перф», «проверь на
гонки», «безопасна ли эта миграция».

## Статус реализации (честно)

- **Полностью реализовано и протестировано:** все фиксы скриптов; `verify_findings.py`,
  `change_risk.py`, `calibration.py` (компилируются + покрыты регрессиями); rubric; все
  13 чек-листов; 10 eval-регрессий (`ALL REGRESSIONS PASSED`); дисциплина, version-aware,
  grounded-perf, counterfactual-проверка и diff-mode шаги в SKILL.md.
- **Каркас (работает, раскрывается на живом прогоне):** `score.py` требует реального
  прогона ревью для метрик; сабагент-верификатор — инструкция для Claude Code, его
  поведение зависит от модели; `calibration.py` полезен только когда копится история
  исходов; `change_risk.py` callers-оценка — best-effort через grep; корпус фикстур
  покрывает по одному сигнатурному классу на модуль (24 пары) — расширяй под свой
  стек добавлением dict в `evals/build_fixtures.py` (см. `evals/README.md`).
- **Сознательно НЕ добавлено** (чтобы не раздувать always-load и не размывать фокус):
  accessibility/i18n-аудит, полноценный IaC-скан, карбон-метрики, committee из спорящих
  агентов. Это отдельные скиллы, если понадобятся.

## Тюнинг

Главное место — `checklists/`. Добавляешь свои паттерны в нужный файл или новый
`checklists/your-stack.md` + упоминание в `SKILL.md` Step 5. Жёсткость правится в
секциях «Core review philosophy» и «Operating discipline». Бюджет веб-поиска — Step 4.
