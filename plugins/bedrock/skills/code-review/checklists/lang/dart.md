# Dart / Flutter — language module (CLIENT threat model)

**Threat model is client-side, not server-side.** A Flutter app ships to the user's device and
can be decompiled, repackaged, run on a rooted/jailbroken phone, and MITM'd. So the spine's
server injections (SQLi, SSRF) mostly **don't** apply to client code; the real risks are
secrets in the bundle, insecure local storage, transport, and platform integration. The
governing rule: **the client is hostile territory — anything shipped in the app is readable,
and the only real trust boundary is the backend.** (If this is Dart *server* code — `dart:io`,
Shelf, Dart Frog — then the normal spine/server module applies; state which you're reviewing.)
Built on `checklists/taint-spine.md`. Static helpers: `dart analyze`, MobSF on the built
APK/IPA, OWASP Dependency-Check / `dart pub` audit.

## Client risk categories (OWASP Mobile/MASVS)

- **Secrets in the bundle (M-creds).** Hardcoded API keys, Stripe/AWS/Firebase-admin keys,
  OpenAI keys, signing secrets in Dart source, asset files, or `.env` bundled via
  `flutter_dotenv`/`--dart-define`. **All of these ship in the binary and are extractable** —
  `--dart-define`/dotenv is configuration, *not* security. Any production secret here is a
  finding; the only fix is to move it behind the backend (the client gets a short-lived,
  scoped token).
- **Insecure local storage (M9).** Tokens/PII in `SharedPreferences`, plain `Hive`/`sqflite`,
  files, or logs in plaintext. Safe: `flutter_secure_storage` (→ iOS **Keychain** / Android
  **Keystore**); encrypt at rest with a key from secure hardware, never a hardcoded key.
- **Insecure transport (M5).** Non-HTTPS endpoints, disabled cert validation
  (`HttpClient..badCertificateCallback = (_,__,___) => true` — flag instantly), no certificate/
  SPKI pinning on a high-value app (banking/payments). Pinning isn't mandatory for every app —
  note the app class.
- **Deeplink / platform-channel / IPC.** Untrusted data arriving via deep links / app links,
  custom URL schemes, or `MethodChannel` from native, used without validation (navigation to
  arbitrary routes, auth-token theft via a malicious link). Validate and allowlist deeplink
  targets; don't expose sensitive `MethodChannel` operations to other apps.
- **WebView (`webview_flutter`).** Loading untrusted URLs, enabling JS + a JS channel that
  exposes native capability, `file://` access → the mobile equivalent of XSS-to-native-bridge.
- **Client-side trust mistakes.** Enforcing auth/price/role only in Dart (the user controls the
  client — always re-check on the server); leftover debug code, `print()`/logging of tokens,
  mock/test endpoints, `kReleaseMode` not gating debug behavior; no code obfuscation
  (`flutter build --obfuscate`) on sensitive logic (slows, doesn't stop, reverse engineering).

## Footguns (Dart language)

- **Swallowed async errors** — an un-awaited `Future` whose error is lost; empty `catch {}`;
  unhandled `Future` on a security path.
- **`late` misuse** — `LateInitializationError` (a panic/DoS) when a `late` field is read before
  set on a user-driven path.
- **Null-assertion `!`** on external/nullable data → runtime crash.
- **Weak randomness** — `dart:math` `Random()` for tokens; use `Random.secure()`.

## Sanitizer idioms (what "safe" looks like)

- No production secrets in the app — short-lived backend-issued tokens only.
- `flutter_secure_storage` for tokens/PII; HTTPS everywhere; pinning where the app class warrants.
- Deeplink/MethodChannel/WebView inputs validated and allowlisted; no native bridge exposed to
  untrusted web content.
- Server-side enforcement of every auth/authz/price decision; `Random.secure()` for tokens;
  release builds obfuscated with debug code stripped.

Severity per `references/severity-rubric.md`: a live production secret in the bundle or disabled
cert validation on a payments app → CRITICAL/HIGH; plaintext token storage → HIGH; client-only
auth enforcement → HIGH (the server is the real gate).
