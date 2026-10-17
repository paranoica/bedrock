# {project}

{one line: what the product is and for whom}

## Knowledge base
`~/projects-memory-bank/{project}/` — start at `entry.md`. Decisions, architecture, failures
and runbooks live there, not here.

## Commands
Run them through `bedrock cmd <name>`; heavy ones wait for the machine lock.

| Name | What it does | Pitfalls |
|---|---|---|
| setup | {…} | {…} |
| test | the full suite | {…} |
| test-related | the tests for given files | {…} |
| lint | {…} | {…} |
| typecheck | {…} | {…} |
| build | {…} | {…} |

## Critical zones
Changes here get the full review (R3): {globs, one line each, with why}.

## Rules
{project-specific rules only; the plugin carries the general ones}
