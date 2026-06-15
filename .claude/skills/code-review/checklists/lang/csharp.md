# C# / .NET — language module

Covers C# on .NET Framework 4.x and modern .NET (5–9), ASP.NET Core/MVC, EF Core/Dapper/ADO.NET,
WCF/WebForms legacy. Server-side threat model. Built on `checklists/taint-spine.md`. Static
helpers: Roslyn analyzers (the `CAxxxx` security rules cited below), Security Code Scan,
Semgrep; `dotnet list package --vulnerable` / OSV for deps. Deserialization findings →
**CRITICAL** (ysoserial.net makes gadget RCE turnkey).

## Sinks by S-category

- **S6 Deserialization (top .NET RCE class).**
  - **`BinaryFormatter.Deserialize`** on any untrusted bytes — cannot be made safe; obsolete
    since .NET 5 (warning SYSLIB0011), and in **.NET 9 it throws on use**. Same for
    `NetDataContractSerializer`, `SoapFormatter`, `ObjectStateFormatter`/`LosFormatter` (ASP.NET
    ViewState), `LosFormatter`. Flag every call. Fix = replace the mechanism, not "validate".
  - **Json.NET (`Newtonsoft.Json`) with `TypeNameHandling` != `None`** (`Auto`/`All`/`Objects`)
    → attacker picks the type to instantiate = RCE (Roslyn **CA2328/CA2326**). Default is
    `None`; flag any code that sets it without a strict `ISerializationBinder` allowlist.
  - Safe: `System.Text.Json` `JsonSerializer.Deserialize<ConcreteType>(...)` (binds to a known
    type, never instantiates arbitrary types), or Json.NET with `TypeNameHandling.None`.
- **S1 SQL** — `new SqlCommand("... " + x)` / string-interpolated SQL, EF `FromSqlRaw($"...{x}")`
  / `ExecuteSqlRaw` with interpolation, Dapper `Query("... " + x)`. Safe: `SqlParameter` /
  `cmd.Parameters.AddWithValue`, Dapper anonymous-object params (`Query(sql, new { x })`), EF
  `FromSqlInterpolated` (parameterizes the interpolation) or LINQ.
- **S3 Command** — `Process.Start` with a shell/`/c`+user string. Use `ProcessStartInfo` with an
  argument list and `UseShellExecute=false`.
- **S4 XSS / template** — Razor `@Html.Raw(user)`, `MvcHtmlString`, writing unencoded to the
  response; Razor auto-encodes `@x` so the risk is the explicit raw escape hatches.
- **S6 XXE** — `XmlDocument`/`XmlReader`/`XmlTextReader` with `DtdProcessing.Parse` and a
  resolver on untrusted XML (modern defaults are safer; legacy `XmlTextReader` is not).
- **S7 Path / S8 SSRF** — `Path.Combine(root, userName)` does **not** stop absolute/`..` escape
  (an absolute second arg replaces root) → validate the resolved path stays under root;
  `HttpClient`/`WebRequest` to a tainted URL → SSRF (allowlist, block metadata/private, redirects).
- **S12 Authz / mass assignment (over-posting)** — MVC model binding straight onto an EF entity
  lets the client set `IsAdmin`/`RoleId` → bind to a view-model/DTO or use `[Bind]`/`[BindNever]`.
  `[Authorize]` missing on a controller/action; IDOR on id from the route.

## Footguns (taint-independent)

- **`async void`** (outside event handlers) — exceptions are unobservable, crash the process.
- **Swallowed exceptions** `catch { }` / `catch (Exception) { }` on security/IO paths.
- **`==` for secret/token compare** — not constant-time; use
  `CryptographicOperations.FixedTimeEquals`.
- **`Random` for security** — predictable; use `RandomNumberGenerator`.
- **`IDisposable` not disposed** (`using` missing) — connection/handle leaks; `HttpClient`
  created per-request (socket exhaustion) — use a single client / `IHttpClientFactory`.
- **Nullable-reference warnings suppressed** with `!` on external data → NRE/DoS.

## Sanitizer idioms (what "safe" looks like)

- `System.Text.Json` to concrete types; Json.NET left at `TypeNameHandling.None`; no
  `BinaryFormatter` anywhere.
- Parameterized `SqlParameter`/Dapper params/EF LINQ or `FromSqlInterpolated`.
- DTO/view-model binding, never the EF entity; `[Authorize]` + server-side ownership checks.
- `RandomNumberGenerator` for tokens; `FixedTimeEquals` for secret comparison;
  `IHttpClientFactory` for outbound calls.

## Framework / version notes

- ASP.NET Core: misconfigured CORS (`AllowAnyOrigin` + credentials), antiforgery disabled on a
  cookie-auth form post, Data Protection keys not persisted across instances (cookie/CSRF token
  invalidation or forgery). Swagger/developer exception page enabled in production.
- Version-gate: `BinaryFormatter` already throws in .NET 9 — on a .NET 9 target the call is a
  build/runtime break, on .NET Framework it's a live RCE. State the target framework.
  Severity per `references/severity-rubric.md`; reachable deserialization/SQLi → CRITICAL.
