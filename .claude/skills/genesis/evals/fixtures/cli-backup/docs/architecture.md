# Architecture — Backup CLI

## Components
- CLI — argument parsing + config load.
- Core — snapshot / restore / prune logic.
- Target driver — writes/reads snapshots (local at MVP).

## Data model
- A local snapshot **index** per target — a small catalog (id, timestamp, checksum, source path). Entities map to `term:snapshot`.

## Invariants
<!-- @anchor arch:restore-verifies-checksum -->
- Restore verifies checksum — `restore` SHALL verify a snapshot's checksum and abort before writing any file on mismatch.
<!-- @anchor arch:prune-explicit -->
- Prune is explicit — retention SHALL be applied only by an explicit `prune`, never implicitly during `backup`.
