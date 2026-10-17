# Bootstrap — Scaffold Module

Loaded **only** for Stage 2 of the pipeline, and only when both are true: the user chose to build a new production project, **and** no frontend skeleton exists. If a frontend already exists, this module is never loaded — skip straight to Stage 3.

This module raises a frontend skeleton. It is stated at the **level of principle** — it never bakes one project's concrete values into itself.

## The universal vs the concrete

**Universal scaffold principles (this module carries these):**
- The frontend is split into modular files with a length limit per file.
- A project config document for agents exists (a `CLAUDE.md`).
- Code is consistent — one indentation, one naming convention, one structure.
- The structure is predictable — sections, components, styles, assets each have an obvious home.

**Concrete values (this module never hard-codes — it reads or asks):**
- Exact indentation, exact file-length limit.
- Folder names and structure (`apps/frontend`, `src/`, etc.).
- Package manager, framework, exact dependencies.

## Where the concrete values come from

1. **A `CLAUDE.md` already exists** in the project (or the user provided one) → **read it** and build the skeleton to *its* rules. Whatever it states — indentation, file-length limit, monorepo layout, stack — the skeleton obeys it. The user's "the way it should be" is honored *because it was read from the project*, not because it was baked into this skill.
2. **No `CLAUDE.md` exists** → do not invent project values. Ask the user for the key parameters — stack, structure, file-length limit, indentation — or take sensible defaults for the chosen stack. Then **create `CLAUDE.md`** with those concrete values, in **both** the repo root and the frontend.

## What the scaffold produces

- A modular frontend structure: a clear place for pages/routes, sections, components, styles, assets, hooks/utilities.
- The package manifest and base configuration for the chosen stack.
- Routing set up.
- A base styling layer ready to receive the design tokens from the pipeline's bridge document.
- `CLAUDE.md` — read-and-extended if it existed, or created in root + frontend if it did not.

## CLAUDE.md handling

- If a root `CLAUDE.md` exists → read it, and **extend** its design section if needed (do not overwrite).
- If a frontend `CLAUDE.md` exists → same.
- If either is missing → create it, carrying the concrete project values (stack, structure, length limit, indentation, design conventions) so future sessions have a source of truth.
- Project-specific design rules accumulated over time live in the project — `.design/rules/` or the project's `CLAUDE.md` — never inside this skill.

## After the scaffold

Once the skeleton stands, the pipeline proceeds to Stage 3 — design-to-code — implementing the design on top of this structure, driven by the bridge token specification.
