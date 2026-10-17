# Postgres / MySQL — database hardening checklist

Deepens `checklists/sql-and-data.md` (which covers query-level injection) at the **server,
privilege, and feature** layer — the misconfigs that turn a foothold into data theft or RCE.
Built on the spine's misconfig stance. Applies to the DB config and to the SQL the app ships
(grants, roles, functions, migrations).

## Privileges & access (least privilege)

- **App connects as a superuser / over-privileged role.** The application DB user should own
  only its tables and have only the DML it needs — not `SUPERUSER`/`rds_superuser`, not
  `CREATE`/`DROP` on the whole schema, not `GRANT` ability. A superuser app connection turns
  any SQLi into full-DB + often host compromise.
- **`PUBLIC` grants** — default `PUBLIC` execute/usage on schemas/functions; `REVOKE` broad
  PUBLIC privileges. MySQL: accounts with `%` host wildcard, `GRANT ALL ON *.*`, anonymous
  accounts, or `FILE` privilege (enables `LOAD_FILE`/`INTO OUTFILE` → read/write host files).
- **Auth config** — Postgres `pg_hba.conf` with `trust` (no password) or broad `0.0.0.0/0 md5`;
  MySQL users with empty passwords or `mysql_native_password` weak hashes; no TLS required
  (`sslmode`/`require_secure_transport`).

## Dangerous features (privilege-escalation / RCE surface)

- **Postgres** — `COPY ... FROM/TO PROGRAM` (command execution, superuser-gated), untrusted
  PL/perlu/PL/pythonu functions, `CREATE EXTENSION` of risky modules, `dblink`/`postgres_fdw`
  reaching internal hosts (SSRF), `lo_import/lo_export` file access. **`SECURITY DEFINER`
  functions** that don't pin `search_path` → a caller can shadow a function/table and run code
  as the definer (privilege escalation) — every `SECURITY DEFINER` must `SET search_path`.
- **MySQL** — `INTO OUTFILE`/`LOAD DATA INFILE` (with `FILE` priv / `secure_file_priv` unset)
  for file read/write → webshell; UDF loading; `sql_mode` not strict (silent truncation/
  coercion data-integrity bugs).
- **`search_path` injection** (Postgres) — relying on a mutable `search_path` so an attacker-
  created object in an earlier schema is resolved first; schema-qualify, pin `search_path`.

## Data protection & integrity

- **No Row-Level Security where multi-tenant** — tenant isolation enforced only in app code →
  one missed `WHERE tenant_id` leaks all tenants; consider RLS as defense-in-depth.
- **No encryption** — at rest (TDE/disk) or in transit (TLS off); secrets/PII in plaintext
  columns; backups unencrypted/public.
- **Missing constraints/transactions** — FK/unique/check constraints absent so bad data slips
  in; multi-step writes without a transaction (cross-ref `concurrency-and-data-integrity.md`);
  `READ UNCOMMITTED`/wrong isolation for the invariant.
- **Logging** — statement logs capturing secrets/PII; error verbosity leaking schema to the app.

## Current CVE classes & version gates (2025–2026)

- **`COPY ... TO/FROM PROGRAM` → RCE (CVE-2025-1094).** A psql input-sanitization flaw let SQLi
  chain into `COPY TO PROGRAM` / `!` meta-commands for shell execution. **`COPY TO PROGRAM` is
  now disabled by default from 14.16** (must be explicitly re-enabled). Flag any code path that
  enables/uses it, and any Postgres below the patched line.
- **`pg_dump`/`pg_restore`/`pg_dumpall` object-name injection (CVE-2025-8713/8714/8715, Aug
  2025).** A crafted object name injects psql meta-commands that run at **restore time** as the
  OS account running `psql`, and SQL as a **superuser** on the restore target (regression of
  CVE-2012-0868; MySQL's CVE-2024-21096 is the analogue). Optimizer-statistics leakage in the
  same set let a user read sampled data a **row-security policy** intended to hide. Patched in
  13.22 / 14.19 / 15.14 / 16.10 / 17.6 — flag older versions and untrusted dump/restore flows.
- **Heap buffer overflows → RCE as the DB OS user** in `pg_trgm`, `pgcrypto`, and multibyte
  text handling (before 18.2 / 17.8 / 16.12 / 15.16 / 14.21). Memory-safety in the engine, not
  just the app — version-gate.
- **Other escalation paths to keep in mind:** crafted trigger/extension RCE (CVE-2023-39417),
  rogue-replica auth bypass (CVE-2019-9193), and `pg_read_file`/`pg_execute_server_program` for
  file read / command execution (superuser-gated — another reason the app must not be superuser).
- **Default/weak credentials** — `postgres:postgres` and empty MySQL root passwords are still
  found in the wild; flag them.

State the exact server version and how you confirmed it; land severity per
`references/severity-rubric.md` (engine RCE / COPY-PROGRAM-reachable → CRITICAL).

## What "safe" looks like

- App role least-privileged (DML on its tables only, no superuser/FILE/CREATE); PUBLIC revoked;
  host/user scoped; TLS required; strong auth (no `trust`/empty passwords).
- `COPY PROGRAM`/UDF/file features disabled or superuser-only; every `SECURITY DEFINER`
  function pins `search_path`; `secure_file_priv` set; strict `sql_mode`.
- RLS for multi-tenant; encryption at rest + in transit; constraints + correct isolation;
  logs scrubbed of secrets.

Cross-refs: query injection → `checklists/sql-and-data.md` + `checklists/taint-spine.md` (S1);
internal reach via `dblink`/`fdw` → SSRF (S8); provisioning → `checklists/infra/terraform.md`.
