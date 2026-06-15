# Decisions — Backup CLI

> Source of truth (highest wins): this file → architecture.md → glossary.md → open-questions.md.

<!-- @anchor decision:cli-surface refs:term:snapshot -->
### D-001 — Commands: backup / restore / list / prune; config via TOML + flags
- Context: a non-interactive, scriptable CLI; predictable behaviour.
- Decision: four subcommands (backup, restore, list, prune); configuration from a TOML file, overridable by flags.
- Consequences: an arg-parsing layer and a config loader.

<!-- @anchor decision:integrity refs:term:snapshot,term:checksum -->
### D-002 — Every snapshot carries a checksum; restore verifies it before writing
- Context: a backup you cannot trust on restore is worthless.
- Decision: store a content checksum per snapshot; restore verifies it and aborts on mismatch before writing any file.
- Consequences: checksum on write, verify on read.

<!-- @anchor decision:retention refs:term:snapshot,term:retention -->
### D-003 — Retention = keep-last-N + max-age; prune is explicit, never automatic
- Context: unbounded snapshots fill the target.
- Decision: a retention policy (keep last N, drop older than max-age), applied only by an explicit `prune` — never during `backup`.
- Consequences: a prune command; backup never deletes.

<!-- @anchor decision:storage-targets refs:term:target,term:snapshot -->
### D-004 — Local filesystem target at MVP; remote behind a pluggable Target interface
- Context: start simple, allow remote later.
- Decision: MVP writes to a local directory target; a Target interface allows remote drivers later. The first remote backend is undecided (see open-questions).
- Consequences: a Target abstraction; only the local driver ships in MVP.
