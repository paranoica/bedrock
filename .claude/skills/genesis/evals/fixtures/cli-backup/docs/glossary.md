# Glossary — Backup CLI

<!-- @anchor term:snapshot -->
**Snapshot** — a point-in-time backup of a source path; identified by id + timestamp; carries a checksum.

<!-- @anchor term:target -->
**Target** — a destination a snapshot is written to (a local directory at MVP; pluggable for remote).

<!-- @anchor term:retention -->
**Retention** — the policy deciding which snapshots `prune` removes (keep-last-N + max-age).

<!-- @anchor term:checksum -->
**Checksum** — a content hash stored with a snapshot and verified on restore.
