# Swift / iOS — language module (CLIENT threat model)

**Client-side threat model**, same governing rule as `checklists/lang/dart.md`: the device is
hostile, the app binary (and its strings) is readable, the only real trust boundary is the
backend. Read the "Client risk categories" in `dart.md` — they apply directly (secrets in the
bundle, insecure storage, transport/pinning, deeplink/IPC, client-only trust). This file is the
iOS/Swift-specific delta. (For *server-side* Swift — Vapor/Hummingbird — apply the normal
spine/server module instead and say so.) Built on `checklists/taint-spine.md`. Static helpers:
Xcode analyzer, SwiftLint, MobSF on the `.ipa`.

## iOS-specific risk categories

- **Keychain misuse.** Tokens/secrets in `UserDefaults`, plist files, Core Data, or files
  instead of the **Keychain** → readable on a jailbroken/backed-up device. Even in Keychain,
  the **accessibility class** matters: `kSecAttrAccessibleAlways` /
  `...AfterFirstUnlock` are weaker than `...WhenUnlockedThisDeviceOnly`; flag overly-permissive
  accessibility for high-value secrets, and `kSecAttrSynchronizable` syncing secrets to iCloud
  unintentionally.
- **App Transport Security (ATS).** `NSAllowsArbitraryLoads = true` in `Info.plist` (disables
  HTTPS enforcement), per-domain ATS exceptions, or a `URLSession` delegate that accepts any
  server trust (`completionHandler(.useCredential, URLCredential(trust:))` without validation) →
  MITM. Pin via the trust evaluation for high-value apps.
- **URL scheme / Universal Link hijacking.** Custom URL schemes can be registered by other apps
  (use Universal Links with verified `apple-app-site-association`); data arriving via
  `application(_:open:)` / `onOpenURL` used unvalidated → auth-token theft, arbitrary navigation.
  Validate and allowlist.
- **Pasteboard / screenshots / backgrounding.** Sensitive data copied to the general
  `UIPasteboard` (readable by other apps), visible in the app switcher snapshot, or in
  notifications. Mark sensitive fields, blur on background.
- **WKWebView.** `WKScriptMessageHandler` bridging native capability to untrusted web content;
  `allowFileAccessFromFileURLs`; loading untrusted HTML/URLs → native-bridge XSS.
- **Jailbreak / integrity.** No detection of a compromised runtime for a high-assurance app;
  debug entitlements (`get-task-allow`) shipped in release.

## Footguns (Swift language)

- **Force-unwrap `!` / `try!` / implicitly-unwrapped optionals** on external/nullable data →
  crash (DoS, and the classic Swift production-crash class). Use `guard let`/`if let`/`try?`.
- **Force-cast `as!`** → crash on unexpected type from a decoded payload.
- **Integer overflow** — `+`/`*` **trap** (crash) on overflow by default; use `&+`/`&*` only
  deliberately, and `ExpressibleByIntegerLiteral` bounds on input-derived sizes.
- **Swallowed errors** — `try?` discarding a security-relevant failure; empty `catch {}`.
- **Weak randomness** — `arc4random`/`Int.random` is fine for non-crypto; use
  `SecRandomCopyBytes` / `CryptoKit` for keys/tokens; never roll your own crypto.

## Sanitizer idioms (what "safe" looks like)

- Secrets only as short-lived backend tokens; long-lived secrets in Keychain with
  `WhenUnlockedThisDeviceOnly` and no unintended iCloud sync.
- ATS left enabled (no arbitrary-loads); server-trust validated/pinned for high-value apps.
- Universal Links (verified) over custom schemes; open-URL inputs validated.
- `guard let`/`if let`/`try?` over force-unwrap on external data; `CryptoKit`/`SecRandom` for crypto.
- Every auth/authz/price decision re-enforced server-side.

Severity per `references/severity-rubric.md`: secret in `Info.plist`/`UserDefaults`, ATS
arbitrary-loads, or trust-all `URLSession` on a payments app → CRITICAL/HIGH; force-unwrap DoS on
a request path → MEDIUM/HIGH by blast radius.
