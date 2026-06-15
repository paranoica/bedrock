# Java — language module

Covers Java (JDK 8–21), Spring/Spring Boot, Jakarta/Java EE, JDBC/JPA/Hibernate, servlet
stacks. Server-side threat model. Built on `checklists/taint-spine.md`. Static helpers:
Semgrep (Java rulesets), SpotBugs + find-sec-bugs, Gadget Inspector (deserialization chains),
`mvn dependency-check` / OSV for the CVE layer. Deserialization & JNDI findings are
**CRITICAL** — they are direct RCE (Equifax/Struts CVE-2017-9805, Log4Shell lineage).

## Sinks by S-category

- **S6 Deserialization (the marquee Java RCE class)** — `ObjectInputStream.readObject()` on
  any attacker-influenced bytes → gadget-chain RCE (commons-collections, etc.). Also
  `XMLDecoder.readObject`, `XStream` without allowlist, Jackson with **default typing**
  enabled (`enableDefaultTyping()` / `@JsonTypeInfo` on `Object`), SnakeYAML `new Yaml().load`
  on untrusted input (use `SafeConstructor`), Spring-Kafka mis-set
  `spring.json.trusted.packages=*` (CVE-2023-34040 class). Safe: don't deserialize untrusted
  native streams at all; if forced, a JEP 290 `ObjectInputFilter` allowlist; Jackson with
  default typing off and concrete types.
- **S4 Expression-language / SpEL injection** — `SpelExpressionParser().parseExpression(user)`,
  Spring `@Value` with user data, `${}`/`#{}` reaching an evaluator, Thymeleaf/OGNL (the
  Spring4Shell / Struts OGNL lineage) → RCE. Never evaluate user-supplied expressions.
- **S6/S8 JNDI injection** — `new InitialContext().lookup(userControlled)` →
  `ldap://evil/Exploit` loads a remote factory = RCE. This is the Log4Shell mechanism. Never
  pass user data to a JNDI lookup; this is the highest-severity quick win in a Java review.
- **S1 SQL** — `stmt.executeQuery("... " + x)`, JPA/Hibernate `createQuery("... " + x)` /
  `createNativeQuery` with concatenation. Safe: `PreparedStatement` with `?` placeholders;
  JPQL/criteria with bound parameters. `@Query` with SpEL/concat in Spring Data.
- **S6 XXE** — `DocumentBuilderFactory`/`SAXParserFactory`/`XMLInputFactory`/`Transformer`
  parsing user XML **without** disabling external entities and DTDs
  (`setFeature("disallow-doctype-decl", true)` / `XMLConstants.FEATURE_SECURE_PROCESSING`).
- **S3 Command** — `Runtime.getRuntime().exec(userStr)`, `ProcessBuilder` with a shell. Use a
  fixed arg list, no shell.
- **S7 Path / S8 SSRF** — `new File(userPath)` / `Files.newInputStream` traversal;
  `new URL(userUrl).openConnection()` / `RestTemplate`/`WebClient`/`HttpClient` to a tainted
  URL → SSRF (allowlist + block metadata/private, beware redirects + DNS rebind). Zip-slip in
  archive extraction (`new File(dir, entry.getName())` without confinement).
- **S12 Authz / mass assignment** — Spring binding a whole request to an entity
  (`@ModelAttribute` / `@RequestBody` onto a JPA entity) lets the client set fields it
  shouldn't (role, isAdmin) → use a DTO + explicit mapping. IDOR: loading by id from the
  request with no ownership check.

## Footguns (taint-independent)

- **`equals`/`hashCode` mismatch**, mutable keys in a `HashMap` → lost entries / logic bugs.
- **Non-constant-time secret compare** — `String.equals`/`Arrays.equals` on tokens/HMACs;
  use `MessageDigest.isEqual` / `MessageDigest`-based constant-time compare.
- **`SimpleDateFormat`/`Random` not thread-safe / not crypto** — `java.util.Random` for tokens
  is predictable (use `SecureRandom`); shared `SimpleDateFormat` corrupts under concurrency.
- **Autoboxing NPE** — unboxing a `null` `Integer` into `int`; `Optional` ignored.
- **Resource leaks** — streams/connections not in try-with-resources; swallowed exceptions
  (`catch (Exception e) {}`) on security/IO paths.
- **Integer overflow** silently wraps (no exception) — size/index math from input.

## Sanitizer idioms (what "safe" looks like)

- No native deserialization of untrusted data; Jackson default-typing OFF + concrete types;
  JEP 290 filter where unavoidable.
- `PreparedStatement`/bound JPQL params; never string-built SQL.
- XML parsers with DTD/external-entity disabled and secure-processing on.
- DTOs (not entities) bound to requests; server-side ownership checks on every object access.
- `SecureRandom` for tokens; `MessageDigest.isEqual` for secret comparison.

## Framework specifics (Spring)

- Actuator endpoints exposed (`/actuator/env`, `/heapdump`, `/jolokia`) → info leak / RCE chain.
- `@CrossOrigin("*")` with credentials; CSRF disabled (`http.csrf().disable()`) on a
  cookie-auth app. `permitAll()` over-broad; method security annotations missing.
- Spring Data `@Query` with concatenation/SpEL; `findBy*` with no tenant filter.

## Version notes

- JEP 290 (JDK 9 / backported) provides serialization filters — note whether the project sets
  one. Log4j ≥ 2.17 closed the JNDI lookup default; flag a pre-2.17 `log4j-core` (CVE-2021-44228).
  Severity per `references/severity-rubric.md`; reachable deserialization/JNDI/SpEL → CRITICAL.
