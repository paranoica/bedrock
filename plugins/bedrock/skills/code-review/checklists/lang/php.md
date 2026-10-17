# PHP — language module

Covers PHP 7.x–8.x, Laravel, Symfony, WordPress/plugin code, raw PHP. Server-side threat
model. Built on `checklists/taint-spine.md`. Static helpers: Psalm/PHPStan (taint mode),
Semgrep PHP rules, `composer audit` / OSV for deps. Sources are the superglobals `$_GET`,
`$_POST`, `$_REQUEST`, `$_COOKIE`, `$_FILES`, `$_SERVER` (incl. headers like
`HTTP_X_FORWARDED_FOR`, `PHP_SELF`).

## Sinks by S-category

- **S6 Object injection (the signature PHP RCE class)** — `unserialize($userData)` instantiates
  arbitrary classes and fires magic methods (`__wakeup`, `__destruct`, `__toString`,
  `__call`) → Property-Oriented-Programming (POP) gadget chains → RCE/SQLi/file-write. Also
  **`phar://` deserialization**: passing a tainted path to a filesystem function
  (`file_exists`, `fopen`, `getimagesize`, `include`) with a `phar://` wrapper triggers
  unserialize on the Phar metadata. Safe: never `unserialize` untrusted input — use
  `json_decode`; if unavoidable, `unserialize($x, ['allowed_classes' => false])`.
- **S4 Code eval / dynamic include** — `eval($user)`, `assert($user)` (executes code in PHP <8),
  `create_function`, `preg_replace` with the `/e` modifier (old), `call_user_func($_GET[...])`,
  variable functions `$fn()` / variable-variables `$$x`. RCE.
- **S7 LFI / RFI** — `include`/`require`/`include_once` with user input:
  `include($_GET['page'].'.php')` → local file inclusion (read `/etc/passwd`,
  `php://filter/convert.base64-encode/resource=` to exfil source) and, if
  `allow_url_include=On`, remote file inclusion = RCE. Safe: allowlist of includable files,
  never a path from input; `open_basedir`, `allow_url_include=Off`.
- **S3 Command** — `system`, `exec`, `shell_exec`, `passthru`, `popen`, `proc_open`, backticks
  `` `$cmd` `` with user data. Use `escapeshellarg`/`escapeshellcmd` *and* prefer fixed args.
- **S1 SQL** — string-built queries to `mysqli_query`/`PDO::query`/`->query("... $x")`. Safe:
  PDO prepared statements with bound params (`?`/named), `mysqli` prepared statements. (Eloquent/
  Doctrine DQL with concatenation or `whereRaw($x)` is injectable; bind instead.)
- **S5 XSS** — `echo`/`print`/interpolation of user data into HTML without `htmlspecialchars`
  (with `ENT_QUOTES`); Blade `{!! $x !!}` (unescaped) vs `{{ $x }}` (escaped).
- **S8 SSRF** — `curl_exec`/`file_get_contents` on a tainted URL; `fopen` with a remote wrapper.

## Footguns (taint-independent)

- **Type juggling** — loose `==`/`!=` and `switch` do type coercion: `"0e123" == "0e456"`
  (both treated as 0.0, "magic hash" auth bypass), `"abc" == 0` is **false** in PHP 8 but was
  **true** pre-8 (version-sensitive!), `in_array($x, $a)` without the strict flag. **Use `===`
  for any security comparison** (passwords, tokens, hashes); `hash_equals()` for HMAC/token
  compare (constant-time). `strcmp(array, ...)` returns null → loosely-equal to 0 → bypass.
- **`json_decode`/`unserialize` let the client pick the type**, enabling the juggling above —
  validate the decoded type explicitly.
- **Weak randomness** — `rand`/`mt_rand`/`uniqid` for tokens are predictable; use
  `random_bytes`/`random_int`.
- **`extract($_REQUEST)` / `register_globals`-style** patterns → variable overwrite.
- **Loose file-upload checks** — trusting `$_FILES['..']['type']` (client-set) or the extension;
  validate content and store outside the webroot with a non-executable name.

## Sanitizer idioms (what "safe" looks like)

- `json_decode` instead of `unserialize`; `unserialize(..., ['allowed_classes'=>false])` if forced.
- PDO/mysqli prepared statements with bound parameters.
- `htmlspecialchars($x, ENT_QUOTES, 'UTF-8')` on output; Blade `{{ }}` not `{!! !!}`.
- Allowlist for any dynamic include; `===`/`hash_equals` for security comparisons;
  `random_bytes`/`random_int` for tokens.

## Framework specifics

- **Laravel** — `whereRaw`/`DB::raw`/`selectRaw` with interpolation (S1); mass assignment via
  `Model::create($request->all())` without `$fillable`/`$guarded` (use `$request->validated()`);
  `{!! !!}` in Blade; `env()` used outside config (returns null when cached); debug mode +
  `APP_DEBUG=true` leaking stack traces/secrets; unsigned/`signed` route mismatch.
- **WordPress** — missing `$wpdb->prepare()`, missing nonce checks (`check_admin_referer`),
  capability checks (`current_user_can`) skipped, unsanitized `$_REQUEST` in AJAX/REST handlers.

## Version notes

- Comparison semantics changed in **PHP 8** (`"abc" == 0` is now false) — flag juggling bugs
  against the project's PHP version. `assert()` no longer evals strings in PHP 8.
  Severity per `references/severity-rubric.md`; reachable object injection / LFI-to-RCE / eval
  → CRITICAL.
