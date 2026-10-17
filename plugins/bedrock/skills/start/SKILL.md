---
name: start
description: Start a project with bedrock — a new one by interview, or an existing one by onboarding; writes the base, AGENTS.md, workspace settings and verified commands. Use for "новый проект", "подключи проект", "start a project".
disable-model-invocation: true
---

# Starting a project

Two paths (K1). Both end in the same place: a workspace folder that holds the client
repository untouched, the project's knowledge base, `.claude/bedrock.json` and `AGENTS.md`.

## Triggers
- RU: «новый проект», «подключи существующий проект»
- EN: "start a new project", "onboard this repo"

## 0. The workspace
- The workspace is a folder of the owner's. The client repository sits inside it, untouched
  (D059). Bedrock writes nothing into the client repository.
- Create the knowledge-base folder: `bedrock kb init --code <PREFIX> --project <Name>`.
  The workspace settings come in step 2, so the project is named here.
Done when: `bedrock kb validate` prints `[]`.

## 1a. New project: the interview
Follow `references/interview.md`: branches by what the product has (data, accounts, money,
integrations, surfaces), one open question at a time. A missing answer becomes an open
question, never an invented decision.
Done when: the owner confirmed the interview covers the product.

## 1b. Existing project: onboarding (D045)
1. Cheap facts first: `bedrock map build`, then the LSP.
2. A large unknown area: an `inventory` agent drafts module notes. Every claim cites its code
   line and is marked hypothesis.
3. Verify by running: the tests as a behaviour spec; predict an output, run it, and a
   confirmed prediction turns a hypothesis into a fact.
4. What the code cannot tell (why, agreements): ask the owner or the team in one batch.
5. An old workspace with notes and memory: sift it with the owner, item by item, into the
   base. Bulk moves are checked against their sources by a `verifier` agent.
Done when: entry, status, the module notes and pitfalls exist and validate.

## 2. Workspace settings
Copy `templates/project/bedrock.json` to `<workspace>/.claude/bedrock.json` and fill it:
- `commands`: derived from the project's own files (package.json scripts, Makefile,
  pyproject, CI). Standard names: setup, test (the full suite), test-related (the quick
  check, takes `{args}`), lint, format, typecheck, build, run, e2e. Mark heavy ones
  `"heavy": true`. Run each once with `bedrock cmd <name>`, `test-related` with one test file
  after `--`. `run` starts a server: start it, check it answers, stop it. A command that fails
  is fixed or removed, never kept.
- `critical_zones`: path globs from the repository root (D032).
- `packs`: the domain rule packs that apply (`packs/` in the plugin).
- `kb.roots`: the folders that hold modules.
- `agents`, `compact_window` when the defaults do not fit.
- `autoCompactWindow` in the workspace's `.claude/settings.json` when the project needs a
  window other than the owner's default (D056).
Done when: `bedrock project check` prints `[]`.

## 3. AGENTS.md
Copy `templates/project/AGENTS.md` into the workspace and fill it: one-line summary, the path
of the knowledge-base folder, the commands with their pitfalls, the critical zones.
The project's `MEMORY.md` gets one line pointing to its knowledge-base folder (D027).
Done when: every command in AGENTS.md is one that `bedrock cmd --list` shows.

## 4. The tracker and the plugin
- The tracker the project really uses (Jira, Linear, or none) goes into the entry note.
- Enable the plugin for the workspace (`/plugin` in Claude Code), on the owner's word.
Done when: the entry note names the tracker, and the owner enabled the plugin or said not to.

## 5. Hand over
Tell the owner in three lines: what was set up, what is still open (the open-questions
note), and the first task. Commit the knowledge base.
Done when: `git status --short` in the knowledge-base store (`~/projects-memory-bank` unless
the owner's settings move it) prints nothing.
