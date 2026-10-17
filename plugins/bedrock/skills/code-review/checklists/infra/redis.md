# Redis — infra security checklist (incl. Lua scripting)

Covers Redis/Valkey deployment, app usage, and embedded **Lua** (`EVAL`/`EVALSHA`,
`FUNCTION`). Redis trusts its network and clients by design, so exposure + scripting are the
risk centers. Built on the spine's misconfig stance. The Lua axis lives here (per plan) rather
than as a standalone language module.

## Exposure & auth

- **Bound to a public interface with no auth** — `bind 0.0.0.0` (or no `protected-mode`) and no
  `requirepass`/ACL → anyone on the network runs arbitrary commands. This is the classic
  internet-exposed-Redis breach, and it compounds RediShell: ~330k instances are internet-
  exposed and ~60k have no auth at all, partly because the **official Redis container images
  ship with authentication disabled by default** (57% of cloud environments install Redis as an
  image). Require: bind to localhost/private only, strong `requirepass`/ACLs, `protected-mode
  yes`, TLS (`--tls`) for in-transit, firewall.
- **`CONFIG SET` reachable by the app/attacker → RCE.** With command access, an attacker sets
  `dir`/`dbfilename` and `SAVE`s a crafted file (cron, authorized_keys, webshell, Redis module)
  → host RCE. Disable/rename dangerous commands (`CONFIG`, `FLUSHALL`, `DEBUG`, `MODULE`,
  `SLAVEOF`/`REPLICAOF`, `SAVE`) via `rename-command`/ACL for app users; never expose
  `CONFIG SET` to untrusted callers.
- **`MODULE LOAD`** of an arbitrary `.so` → RCE; `SLAVEOF`/`REPLICAOF` to an attacker master →
  replication-based RCE (historical). Restrict.

## Lua scripting (the embedded-language axis)

- **`EVAL`/`EVALSHA` with a script built from user input** — concatenating user data into the
  Lua source is injection into the script (script injection); pass user data as `KEYS`/`ARGV`,
  never interpolate it into the script body.
- **Sandbox escape → host RCE (RediShell, CVE-2025-49844, CVSS 10.0).** A ~13-year-old
  use-after-free in the Lua interpreter's GC lets a **post-auth** attacker send a crafted Lua
  script, escape the sandbox, and run native code as the Redis process → reverse shell,
  credential theft (`.ssh`, IAM tokens), lateral movement. Lua is enabled by **default**.
  Patched in 6.2.20 / 7.2.11 / 7.4.6 / 8.0.4 / 8.2.2 (2025-10-03); affects Valkey and managed
  services (ElastiCache, Memorystore, Azure Cache). **Version-gate:** flag any Redis below the
  patched line as exploitable; if EVAL isn't needed, deny `EVAL`/`EVALSHA`/`FUNCTION` via ACL
  as the workaround. Earlier escapes also exist (`cjson`/`cmsgpack`/`struct`/`redis.call`
  misuse, global-table tricks).
- Don't accept Lua scripts from clients; ship a fixed, reviewed set. (Same applies to
  OpenResty/`ngx_lua` — see `checklists/infra/web-servers.md`.)
- **Long-running scripts** block the single-threaded server → DoS; bound work and keys touched.

## App-level usage

- **SSRF-to-Redis** — if an attacker controls a URL the server fetches, the Redis line protocol
  (RESP) is newline-tolerant enough to smuggle commands via `gopher://`/CRLF; an internal,
  unauthenticated Redis is then driveable from an SSRF. (Reinforces: auth + bind private.)
- **User input as a key/command** — newlines/CRLF in a user-derived key can confuse RESP; type-
  and content-validate keys. Cache values that are later trusted as code/SQL = second-order
  injection (apply the spine).
- **No memory cap / eviction policy** → memory-exhaustion DoS; secrets cached without TTL/encryption.

## What "safe" looks like

- Private bind + `protected-mode` + strong `requirepass`/ACL + TLS; dangerous commands renamed/
  ACL-denied for app users; `CONFIG SET`/`MODULE`/`SLAVEOF` not reachable by untrusted callers.
- Fixed reviewed Lua scripts only, user data via `KEYS`/`ARGV`; bounded script work.
- Redis reachable only from the app subnet; SSRF allowlist on the app side; `maxmemory` + policy set.

Cross-refs: SSRF mechanics → `checklists/taint-spine.md` (S8); OpenResty Lua →
`checklists/infra/web-servers.md`.
