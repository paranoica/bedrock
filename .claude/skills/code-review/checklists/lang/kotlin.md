# Kotlin — language module (delta over `java.md`)

Kotlin runs on the JVM, so **all of `checklists/lang/java.md` applies** (deserialization, JNDI,
SpEL, SQL, XXE, SSRF, mass assignment, the Spring framework section). Read that first; this is
the Kotlin-only delta. Server stacks: Ktor, Spring Boot (Kotlin), Exposed/jOOQ, plus Android
(which uses the **client** threat model — see notes). Built on `checklists/taint-spine.md`.

## What changes vs Java

- **Null-safety is a language feature, but `!!` and platform types defeat it.** `userInput!!`
  throws NPE → DoS on a request path; values coming from Java APIs are *platform types* (`T!`)
  that bypass null checks silently — flag `!!` on request-derived data and unchecked platform
  values reaching a sink.
- **`runCatching {}` / empty `catch`** swallow failures the same way Java's do — on auth/IO
  paths that hides errors.
- **String templates** `"$x"` are just concatenation — a template built into a SQL/shell/HTML
  string is the same injection as Java `+`. `"SELECT ... WHERE id = $id"` to a raw query is S1.
- **Coroutines** add concurrency hazards: shared mutable state across coroutines without a
  mutex/`Atomic`, `GlobalScope` leaks (unstructured concurrency), blocking calls on a
  coroutine dispatcher starving the pool. Cross-ref `concurrency-and-data-integrity.md`.
- **`data class` + framework binding** — binding a request straight onto a `data class` entity
  has the same mass-assignment risk; use a dedicated DTO.

## Framework specifics

- **Ktor** — `call.receive<T>()` is tainted input (validate beyond type); `call.respondText`
  with user HTML is XSS unless the content type/escaping is correct; routing params unvalidated;
  CORS/CSRF features must be installed explicitly; `Authentication` configured but a route left
  outside the `authenticate {}` block.
- **Exposed / jOOQ** — DSL queries are parameterized and safe; the risk is `.exec("raw $x")` /
  custom SQL with interpolation.

## Android (client threat model)

If this is Android Kotlin, the model flips to client-side (like `dart.md`/`swift.md` once
built): secrets hardcoded in the APK, insecure `SharedPreferences`/SQLite storage of tokens,
exported components/intents (deeplink/IPC), WebView `addJavascriptInterface` + `loadUrl` with
untrusted content, missing certificate pinning, `allowBackup=true` leaking data. State the
model at the top of the report when reviewing Android code.

## Sanitizer idioms

Same as Java, plus: prefer safe-call `?.`/`?:` over `!!` on external data; structured
concurrency (`coroutineScope`) over `GlobalScope`; DTOs over data-class entities for binding.
