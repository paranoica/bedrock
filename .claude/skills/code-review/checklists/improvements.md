# Improvements Checklist

Этот чек-лист — **отдельная фаза ревью**. Запускается ВСЕГДА, после того как пройдены security/perf чек-листы. Цель — найти, что можно улучшить, **даже если кода нормальный и багов нет**.

## Принципиальная разница с багами

- **Bug:** код неправильно работает, или работает с риском. Severity: CRITICAL/HIGH/MEDIUM/LOW.
- **Improvement:** код работает корректно, но можно сделать быстрее / проще / надёжнее. Категория: **IMPROVEMENT** (без severity, но с **impact**: high/medium/low).

Improvements идут **отдельным разделом** в отчёте, после LOW. Не смешивать с багами.

## Жёсткие правила что репортить

Чтобы не залить пользователя шумом, improvement попадает в отчёт **только если выполнено хотя бы одно**:

1. **Measurable speedup** — можно назвать порядок ускорения: «10x на больших списках», «убирает round-trip», «O(n²) → O(n)».
2. **Removes a foot-gun** — текущий код корректен, но легко сломать при правке. Рефакторинг делает следующего автора устойчивым к ошибке.
3. **Significantly less code / simpler** — то же поведение в 2x меньше строк, или замена кастомной логики на стандартную из стд-библиотеки/фреймворка.
4. **Better resource usage** — экономит память, соединения, выделения в hot path.
5. **Modernization with real benefit** — переход на более новую API даёт измеримое улучшение (e.g., async, streams, новый SDK). Не "новее = лучше".

## Что НЕ репортить (anti-noise)

Эти вещи **запрещены** как improvements — заведомо шум:

- **Стилевые предпочтения:** `let` vs `const`, `for` vs `forEach`, single vs double quotes, trailing commas.
- **Naming bikeshedding:** «лучше назвать `data` как `userData`» без существенной причины путаницы.
- **Micro-optimizations без замера:** «`Array.from` чуть быстрее spread» — нет.
- **Premature abstraction:** «вынеси в функцию» если функция вызывается 1 раз.
- **«Можно использовать X библиотеку»** если стандартная решает задачу одинаково хорошо.
- **Type annotations** на переменных где TS их выводит сам.
- **Comments / docstrings missing** — это всегда LOW bug, не improvement.
- **«Можно добавить тесты»** — это отдельный вопрос (можно упомянуть один раз в конце, не на каждый файл).
- **«Использовать TypeScript»** в JS-проекте — это решение уровня архитектуры, не improvement.

Если improvement не проходит ни по одному из 5 критериев выше — выкинуть.

---

## Категории improvements (на что смотреть)

### 1. Скорость

- **Алгоритм:** двойной цикл по тому же массиву → Set. `arr.includes()` в цикле → Set lookup. Linear scan → binary search где сортированно.
- **Параллелизация:** последовательные `await` где можно `Promise.all` / `asyncio.gather`. Только если зависимостей нет.
- **Memoization / caching:** дорогая чистая функция вызывается с теми же аргументами несколько раз — `functools.lru_cache`, `useMemo`, простой Map.
- **Batching:** N запросов где можно один (DataLoader pattern). Даже если это не N+1 (см. perf.md), один запрос на 5 элементов лучше чем 5 запросов.
- **Lazy evaluation:** строится большая структура, используется только часть → генератор / итератор.
- **Streaming где буферится:** читаем файл целиком в память чтобы посчитать что-то → построчное чтение.

### 2. Памяти

- **Лишние копии:** `[...arr].map(...)` где `arr.map(...)` уже создаёт новый. `JSON.parse(JSON.stringify(obj))` для clone → `structuredClone`.
- **Замыкания держащие крупные объекты:** колбек захватывает весь request когда нужен один `req.user.id`.
- **Кэши без лимита размера:** упомянуть `LRU` со ёмкостью.

### 3. Читаемость и foot-guns

- **Кастомная логика → стандартная:** ручной debounce → `lodash.debounce`. Ручной group-by → `Object.groupBy` (ES2024) или `_.groupBy`. Ручная глубокая проверка равенства → `_.isEqual` / `deepEqual`.
- **Magic numbers:** `setTimeout(..., 86400000)` → именованная константа.
- **Параметры в позиционной форме > 3:** `f(true, false, null, 'x')` → объектный аргумент `{enabled, dryRun, ...}`.
- **Глубокая вложенность (>4):** early returns / extract function.
- **Cyclic complexity:** функция > 50 строк с кучей if/switch → разнести по case classes / strategy pattern.

### 4. Современные API в проекте

Только если **по факту лучше** — не просто «потому что новее»:

- **Python:** `pathlib` вместо `os.path.join`; `dataclasses` / `pydantic` вместо ручных classов с `__init__`; f-strings вместо `.format()`; `dict.get(k, default)` вместо `if k in d`; structural pattern matching (3.10+) где много `isinstance` цепочек.
- **JS/TS:** `Promise.allSettled` где нужна устойчивость к partial fail; `AbortController` для отмены fetch'ей; `Array.prototype.at(-1)` вместо `arr[arr.length-1]`; `structuredClone` вместо JSON-trick; native `Object.groupBy` (ES2024); top-level await в ESM модулях; **Node 22+** native `fetch`, `--watch`, `--test` вместо external tools.
- **React:** `useId` для accessibility вместо ручных id; `useDeferredValue` / `useTransition` для тяжёлых обновлений; Server Components / Server Actions в Next 14+ где было «нужно всё на клиенте».
- **SQL:** `INSERT ... ON CONFLICT` вместо «check then insert»; `RETURNING` после INSERT/UPDATE вместо second SELECT; CTE для читаемости сложного запроса; window functions вместо self-join'ов.

### 5. Архитектурные улучшения

Только если ощутимо:

- **Inline'нутая бизнес-логика в HTTP handler:** разнести на handler + service + repository, если handler >100 строк или логика дублируется.
- **God class:** один класс на 600 строк — разнести по ответственности.
- **Дублирующиеся защиты:** одна и та же проверка auth/validation в 5 endpoint'ах → middleware/decorator.
- **Hardcoded коэффициенты политики:** константы лимитов внутри функций → конфиг / DB-driven.
- **Implicit state через глобальные переменные:** `db_connection` как module-level → DI / context.

### 6. Observability

- **Logger без structured fields:** `logger.info(f"User {id} logged in")` → `logger.info("login", extra={"user_id": id})`. Improvement только если в проекте уже используется JSON-logging.
- **Метрик нет на критичных путях:** платёж/auth без counter'а — упомянуть один раз.
- **Tracing context потерян:** `await fetch(...)` в middleware без передачи trace headers — упомянуть если проект уже использует OTel.

### 7. Тесты (только если совсем плохо)

- **Сложная логика без тестов:** функция с 5+ ветками — упомянуть **один раз** (не на каждую такую функцию).
- **Тесты на implementation вместо behavior:** mock'и на internal helpers вместо input/output на public API.

---

## Формат вывода в отчёте

```
## Improvements

### [HIGH IMPACT] Title
**File:** `path/to/file.ext:42`
**Category:** Speed / Memory / Readability / Architecture / etc.

```language
[current code, 5 lines max]
```

**Why:** Один абзац — что это даёт. Желательно с цифрами («10x на массивах >1k», «убирает N+1 round-trip даже если query сам быстрый»).
**Suggested:** Конкретный код после, 5 строк max.
```

**Impact levels** (вместо severity):
- **HIGH IMPACT** — заметное ускорение, или убирает реальный foot-gun, или существенно упрощает код
- **MEDIUM IMPACT** — улучшение есть, но не транформирующее
- **LOW IMPACT** — nit, но достаточно полезный чтобы упомянуть; обычно 1-2 строки правки

**Лимит:** не более **5-7 improvements** на ревью, даже если кажется что больше. Лучше показать 5 самых жирных, чем 20 средних. Если их реально больше — сгруппируй («Несколько мест используют ручной group-by — можно перейти на Object.groupBy: file1:12, file2:34, file3:56»).

---

## Когда вообще писать секцию Improvements

- **Всегда** — даже если 0 багов и 0 improvements, секция «Improvements» содержит одну строку **на языке пользователя** (RU: «Код чистый — ничего существенного не предложу.», EN: "Code clean — nothing substantial to suggest."). Это сигнал, что секция была рассмотрена.
- Если код **частично грязный, частично чистый** — improvements относятся именно к чистой части, к грязной идут bugs.
- В режиме **uncommitted/PR**: только improvements в изменённых файлах (не лезь рефакторить остальной репо).
- В режиме **full-project**: можешь упомянуть архитектурные improvements выше уровня файла, но всё равно лимит 5-7.
