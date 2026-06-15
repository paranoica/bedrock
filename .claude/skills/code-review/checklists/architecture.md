# Architecture & dependency-health checklist

Findings that only show up at the graph level, not line-by-line: layering violations,
cycles, god objects, and dependencies that are dying even if they have no CVE. Read on
**full-project** reviews and on PRs that add cross-module wiring. These are usually
MEDIUM/LOW (maintainability), occasionally HIGH when a layering break is also a security
boundary break.

## Layering violations
- **Skipping layers:** UI/controller reaching directly into the DB/ORM, or a domain layer
  importing a web framework, or business logic embedded in a migration/handler. Identify
  the project's intended layers (from structure/imports) and flag imports that cross them
  the wrong way.
- **Inward/outward dependency direction:** lower-level/core modules importing higher-level
  ones (e.g. `domain` importing `api`). Dependencies should point toward stable cores.
- **Security boundary bypass:** code that reaches a privileged operation without going
  through the auth/validation layer that's supposed to gate it. This one can be HIGH.

## Cycles & coupling
- **Import cycles** between modules/packages — fragile, hard to test, often a sign of a
  missing abstraction. (Even when the language tolerates them.)
- **God object / god module:** one file/class everything depends on; a "utils" or
  "helpers" that has become a dumping ground and couples unrelated areas.
- **Feature envy / leaky encapsulation:** a module reaching deep into another's internals
  instead of a defined interface; shotgun changes (one logical change forces edits across
  many modules) — flag the coupling, not each edit.
- **Duplicated core logic** (the same business rule implemented in 3 places) that will
  drift out of sync — a correctness risk over time.

## Boundaries & contracts
- **Implicit cross-module contracts** with no interface/type boundary — changes silently
  break consumers (overlaps migrations-and-compat for external contracts).
- **Global mutable state / singletons** used as a backchannel between modules.

## Dependency health (beyond CVEs)
OSV (Step 3) finds *known vulnerabilities*. This finds deps that are simply rotting:
- **Unmaintained:** last release years ago, repo archived, open issues piling up. A
  future CVE here will be unpatchable. Flag as a maintainability/risk item.
- **Single-maintainer / bus-factor-1** on a core dependency.
- **Deprecated but still used** where a maintained successor exists.
- **Heavy dep for trivial use:** a large library pulled in for one function — bloat and
  surface area. Suggest inlining or a lighter alternative.
- **Multiple libraries doing the same job** (two HTTP clients, two date libs) — pick one.
- **Pinned to an ancient major** far behind current, accumulating migration debt.
(Confirm "unmaintained/deprecated" before asserting it — check the package page; don't
guess release dates.)

## How to look
- Sample the import graph: for key modules, list what they import and what imports them.
- Look at directory structure for the intended architecture, then find the imports that
  betray it.
- For dep health, cross-reference the lockfile with what's actually imported (unused deps
  are also worth a LOW note).

## What NOT to flag
- Pragmatic shortcuts in small codebases where layering ceremony would be overkill.
- A "utils" module that's actually small and cohesive.
- Cycles the language/build handles cleanly and that are genuinely local.
- Older-but-stable deps that are maintained and have no better alternative ("old" ≠ "bad").
- Architecture preferences that are just your taste — keep these LOW and few.
