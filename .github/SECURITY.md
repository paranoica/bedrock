# Security policy

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue:

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on this repository, or
- email the maintainer listed in `.github/CODEOWNERS`.

Include what an attacker could do, the affected file/path or surface, and minimal reproduction steps.
You'll get an acknowledgement; please allow reasonable time to fix before public disclosure.

## Scope

This is a project template. Report issues in the template's own tooling (the skills, the scripts
under `tools/` and `.claude/skills/`). Vulnerabilities in a project *generated from* this template
belong to that project's own security policy.

## For maintainers

Dependency and code scanning run in CI; the `code-review` skill is the in-repo reviewer for risky
surfaces (auth, money, migrations) — run the full gate there, never a light pass.
