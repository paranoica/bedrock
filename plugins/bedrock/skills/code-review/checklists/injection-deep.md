# Injection Deep-Dive Checklist

The non-negotiable sweep. Run this against every entry point. Injection bugs are the #1 source of breaches in real-world post-mortems — this checklist exists because the rest of the security check is not enough.

## How to use

For every function that touches untrusted input, ask: **does this input reach a sink unchanged or only string-escaped?** If yes — flag, unless you can prove the sink is safe (parameterized query, parser, sandboxed eval, etc.).

Untrusted sources include: `req.body`, `req.query`, `req.params`, `req.headers`, `request.GET/POST/FILES`, WebSocket messages, queue messages, environment variables when set by user-facing config, file uploads, third-party API responses, OAuth tokens, JWT claims (yes, even after verification — the payload is attacker-controlled).

---

## 1. SQL Injection

**Sinks to grep for:**
- Raw string concatenation in any query: `f"SELECT ... {x}"`, `` `SELECT ... ${x}` ``, `"SELECT ... " + x`
- `.raw()`, `.query(sql)`, `executeRaw`, `text()` in ORMs (SQLAlchemy `text()`, Prisma `$queryRawUnsafe`, Django `.raw()`)
- Dynamic table names / column names — these CAN'T be parameterized, must be allowlisted

**Patterns to flag:**
```python
# BAD
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# Even with str() — still bad
cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))

# GOOD
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```
```typescript
// BAD
db.query(`SELECT * FROM users WHERE email = '${email}'`)
// "Parameterized" but with template literal — still bad
db.$queryRawUnsafe(`SELECT * FROM users WHERE id = ${id}`)

// GOOD
db.query('SELECT * FROM users WHERE email = $1', [email])
db.$queryRaw`SELECT * FROM users WHERE id = ${id}`  // tagged template, safe
```

**Edge cases:**
- ORDER BY column from user input → allowlist of column names, never user string
- LIMIT/OFFSET from user input → cast to int, validate range
- `LIKE` queries — even parameterized, `%` and `_` from user input let them search broader; usually fine, but flag if pattern is sensitive
- Stored procedures called with dynamic SQL inside — same problem one level down

## 2. NoSQL Injection

**MongoDB:** `db.users.findOne({ email: req.body.email })` where `req.body.email = { $gt: "" }` returns the first user. Always type-check or use a schema validator (zod, joi, pydantic) BEFORE the query.

**Redis:** Command injection via unfiltered input to `eval`, `script load`. Key names with newlines can confuse RESP. Less common but worth checking if user input becomes a Redis key.

## 3. Command Injection

**Sinks:**
- `child_process.exec`, `child_process.execSync` (Node) — `spawn` with array args is safer
- `os.system`, `subprocess.run(cmd, shell=True)`, `subprocess.call(cmd, shell=True)` (Python)
- Any template that builds a shell command from user input

**Patterns to flag:**
```python
# BAD
subprocess.run(f"convert {filename} out.png", shell=True)
os.system("ping " + host)

# GOOD
subprocess.run(["convert", filename, "out.png"], shell=False)  # arg array
```
```javascript
// BAD
exec(`git log ${branch}`)
// GOOD
execFile('git', ['log', branch])
```

**Sneaky one:** `subprocess.run([...], shell=False)` is safe for the shell, but if the binary itself parses its own args dangerously (e.g., `git` with `--upload-pack`), there's still risk. Allowlist values where possible.

## 4. XSS (Cross-Site Scripting)

**Stored / Reflected:**
- React: `dangerouslySetInnerHTML={{ __html: userContent }}` — flag every occurrence, demand sanitization (DOMPurify) or proof the source is trusted
- Direct DOM: `el.innerHTML = userContent` — same
- Template engines: Jinja2 with `|safe`, Django with `mark_safe`, Handlebars `{{{triple}}}` — flag

**DOM XSS:**
- `eval(window.location.hash)` — obvious but still happens
- `setTimeout(userString)` / `setInterval(userString)` — string form is `eval` in disguise
- `new Function(userString)`
- `document.write` with anything user-derived

**Framework gotchas:**
- Next.js: rendering `searchParams` directly into HTML attributes without escaping
- Server components passing unsanitized strings to client components that render HTML

## 5. SSRF (Server-Side Request Forgery)

Anywhere the server fetches a URL the user supplied:
```python
requests.get(user_url)
urllib.request.urlopen(user_url)
```
```javascript
fetch(userUrl)
axios.get(userUrl)
```

**What to demand:**
- URL parsing and **scheme allowlist** (`http`, `https` only — block `file://`, `gopher://`, `dict://`, `ftp://`)
- **Host allowlist** OR explicit blocklist of internal ranges: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (AWS metadata!), `::1`, `fc00::/7`, `fe80::/10`
- DNS rebinding: resolve once, validate, then connect to the resolved IP, not the hostname
- For cloud envs, **block 169.254.169.254 hard** — metadata endpoint is the SSRF crown jewel

**Broken defenses to actively flag (these get shipped a lot):**
- **Substring check:** `if "127.0.0.1" in url: block` — bypassed by `http://2130706433/` (decimal IP), `http://0x7f000001/`, `http://127.1/`, `http://[::ffff:127.0.0.1]`, IPv6 forms, DNS names that resolve to loopback.
- **Hostname blocklist without IP resolution:** attacker controls `evil.com` DNS, points it at `169.254.169.254`. Hostname check passes, request still hits metadata.
- **Resolve-then-fetch with different resolutions:** first DNS lookup for validation, second DNS lookup for the actual `requests.get` — between them, attacker's authoritative DNS returns a different answer (DNS rebinding).
- **Library-level redirect following:** allowed URL returns `Location: http://169.254.169.254/...` and the HTTP client auto-follows. Demand `allow_redirects=False` + manual revalidation, or a wrapped HTTP client that re-validates every hop.

## 6. XXE (XML External Entity)

Any XML parsing of user-supplied data. Demand external entity resolution be disabled.

```python
# BAD (lxml without protection)
etree.fromstring(user_xml)
# GOOD
parser = etree.XMLParser(resolve_entities=False, no_network=True)
etree.fromstring(user_xml, parser)
```

In Python stdlib, `xml.etree.ElementTree` is *mostly* OK in modern versions but use `defusedxml` to be safe. In Node, `xml2js` and `fast-xml-parser` need explicit config.

## 7. Deserialization

The classic RCE path. Flag immediately if ANY of these touch untrusted bytes:
- Python: `pickle.loads`, `cPickle.loads`, `marshal.loads`, `shelve` opened on user-supplied path
- Node: `node-serialize`, `serialize-javascript` deserialization, YAML with default loader (`js-yaml` `load` without `JSON_SCHEMA`)
- Python YAML: `yaml.load(x)` without `Loader=SafeLoader` — `yaml.safe_load` is the fix

**No exceptions.** If user data goes to pickle.loads, that's a CRITICAL.

## 8. Prototype Pollution (JS/TS specific)

Look for object merging / cloning from user input:
- `Object.assign({}, userObj)` — vulnerable if `userObj` has `__proto__`
- `lodash.merge`, `lodash.set`, `lodash.defaultsDeep` — historically vulnerable, check version
- `JSON.parse(userInput)` then merging the result into config
- Setting properties from user keys: `obj[userKey] = value` where `userKey` could be `__proto__` or `constructor`

**Defense:** `Object.create(null)`, validated allowlist of keys, schema validation before merge.

## 9. Path Traversal

Whenever a user-supplied string becomes part of a filesystem path:
```python
open(f"./uploads/{filename}", "rb")  # filename = "../../etc/passwd"
```
```javascript
fs.readFile(`./uploads/${filename}`)
```

**Demand:**
- `path.resolve` + check the result starts with the intended base directory
- Reject any input containing `..`, `/`, `\`, null bytes
- For filenames specifically: regex-allowlist `[a-zA-Z0-9._-]+`

## 10. Template Injection (SSTI)

When user input goes into a template string:
- Jinja2: `Template(user_string).render()` — RCE via `{{ ''.__class__.__mro__[1].__subclasses__() }}`
- Mako, Twig, ERB, Handlebars (with helpers), Pug: same family of issues
- Even f-strings if `eval`-equivalent constructs follow

User input should be a **template variable**, never the template body.

## 11. LDAP / SMTP / Header injection

- LDAP: parameterize filter strings, escape `()*\` in user input
- SMTP: CR/LF in user-supplied email headers → header injection → mail spoofing
- HTTP response headers: CR/LF in any header set from user input → response splitting (mostly mitigated in modern frameworks, but verify)

## 12. Open Redirect

`res.redirect(req.query.next)` — if `next` isn't validated, attackers craft phishing links. Validate against an allowlist of paths or hosts.

**Common broken validations to flag:**
- `if next.startswith("/"): redirect(next)` — bypassed by `//evil.com` (protocol-relative URL) and `/\evil.com` in some parsers. Demand parsing with `urlparse` and explicit host check.
- Substring check like `"mysite.com" in next` — bypassed by `https://mysite.com.evil.com` or `https://evil.com?x=mysite.com`.
- Allowing any URL whose hostname "looks like" yours via regex without anchors.

The only correct approach is: parse the URL, take the host, compare against an explicit allowlist set.

## 13. ReDoS — Regular Expression Denial of Service

Patterns with **nested quantifiers** or **alternation with overlap** cause catastrophic backtracking on crafted inputs. A single request can lock a CPU core for seconds-to-hours.

**Patterns to flag:**
- `(a+)+`, `(a*)*`, `(.+)+` — nested quantifiers
- `(a|a)*`, `(a|ab)*` — alternation with overlap
- Anchorless regex on long input with `+` or `*` quantifiers

**Real examples that have caused outages:**
```python
re.match(r"^([a-zA-Z0-9]+)+@example\.com$", user_input)  # Cloudflare 2019 incident pattern
re.match(r"^(\w+\s?)*$", user_input)                      # Stack Overflow 2016 outage pattern
re.compile(r"^(([a-z])+.)+[A-Z]([a-z])+$")               # classic textbook ReDoS
```

**Fix:**
- Refactor to non-backtracking form (atomic groups, possessive quantifiers — limited in Python's `re`, full in `regex` module).
- For email/URL/etc. validation, use a dedicated library (`email-validator`, `validators`) not a hand-rolled regex.
- Always set a timeout (Python `regex` module supports it, JS does not natively → run regex in a worker with a timeout).
- For Node, the `safe-regex` package can pre-screen patterns at build time.

If you see ANY user-controlled input feeding into a regex, mentally trace whether nested/overlapping quantifiers exist. If yes → **HIGH**.

## 14. XML Bombs (Billion Laughs / Quadratic Blowup)

Even without external entity fetching, an XML doc can DoS the parser via entity expansion:
```xml
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  ...
]>
```
A small file expands to gigabytes in memory.

**Defense:** Same as XXE — use `defusedxml` (Python) which disables entity expansion. `lxml` with `XMLParser(resolve_entities=False, huge_tree=False)`. Node `fast-xml-parser` has size/depth limits — set them.

If XML input is parsed from user-controlled bytes and `defusedxml`/equivalent isn't used → **HIGH** (DoS) or **CRITICAL** if XXE is also possible (file read / SSRF).

## 15. Zip Slip / Tar Slip / Archive Path Traversal

When extracting user-uploaded archives, entry names like `../../../../etc/passwd` escape the extraction directory.

**Sinks to flag:**
- Python: `zipfile.ZipFile(f).extractall(dest)`, `tarfile.open(f).extractall(dest)` — neither sanitizes by default in older versions. Python 3.12+ added `filter='data'` for tarfile.
- Node: `unzipper`, `node-tar` (older versions), `adm-zip` — check the version, use `filter` callbacks.

**Defense:**
```python
import os
for member in zip_file.namelist():
    target = os.path.realpath(os.path.join(dest, member))
    if not target.startswith(os.path.realpath(dest) + os.sep):
        raise ValueError(f"Unsafe path: {member}")
```
For tar: also check `member.issym()` / `member.islnk()` — symlinks/hardlinks inside the archive can escape after extraction.

Any unsanitized `extractall` on user input → **CRITICAL** (arbitrary file write, often RCE via writing to startup paths).

## 16. CSV Injection (Formula Injection)

When user input is written to a CSV/XLSX file that downstream users open in Excel/Sheets, values starting with `=`, `+`, `-`, `@`, `\t`, `\r` execute as formulas:
```
=2+5+cmd|'/c calc.exe'!A1
```
Opening this in Excel runs `calc.exe`. Variants exist for DDE, HYPERLINK exfil, etc.

**Where this bites:**
- "Export to CSV" features that include user-supplied content (names, comments, etc.)
- Audit logs exported by admins
- Customer support tools dumping ticket content

**Defense:** Prefix risky values with `'` (single quote), or escape leading dangerous chars. Use a library like `tablib` with the right escape settings.

Flag any CSV export path that includes user-derived strings without escaping → **MEDIUM** (requires user to open the file, but very real).

---

## How to write the finding

If you find ANY of the above, the finding is **CRITICAL** or **HIGH** depending on exploitability:
- Pre-auth, server-side, with clear taint flow → **CRITICAL**
- Post-auth or requires admin → **HIGH**
- Theoretical (would require unlikely conditions) → **MEDIUM** but explain why exploitation is hard

Always include:
- The exact tainted source → sink path
- A proof-of-concept payload that would trigger it (even if hypothetical: `POST /api/search { "q": "' OR 1=1 --" }`)
- The fix, with code

If you're not sure it's actually exploitable but it smells wrong, mark as **MEDIUM "needs verification"** and explain what to test.
