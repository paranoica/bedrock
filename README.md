# bedrock

A working system for [Claude Code](https://code.claude.com), packaged as a plugin and a
marketplace. It turns a coding session into a loop: a plan before code, a test that fails
before the fix, a review by a separate agent before a pull request, and a knowledge base that
stays in step with the code.

It is built for one developer who works across several client projects, and it is opinionated
about that: the owner decides, Claude does the work, and nothing leaves the machine unasked.

## Install

```
/plugin marketplace add paranoica/bedrock
/plugin install bedrock@bedrock
```

or, from a local checkout, `claude --plugin-dir ./plugins/bedrock`. Then run `bedrock doctor`
(the plugin puts `bedrock` on the PATH of the session) to see what the machine has and lacks.

Requirements: Claude Code, git, Python 3.12+. Optional: uv (`uvx`), Node 20+, gitleaks, age,
libnotify, folio, faster-whisper. `bedrock doctor` says what each one is for.

## What is in it

| Part | Where | What it does |
|---|---|---|
| Skills | `plugins/bedrock/skills/` | the working loop (`day`), root-cause debugging (`debug`), the review gate (`review`, `code-review`), the knowledge base (`kb`, `handoff`, `ask`), people and texts (`call`, `doc`, `humanize`), the week (`retro`, `arch`, `triage`), autonomy (`night`), project start (`start`), testing (`hunt`, `e2e`), design (`design-creator`), the navigator (`next`), writing skills (`writing`) |
| Agents | `plugins/bedrock/agents/` | twelve roles with a model, an effort and a turn cap: inventory, researcher, analyst, critic, verifier, reviewer, security reviewer, implementer, implementer without tests (prose and config), architect, escalation, bug hunter |
| Hooks | `plugins/bedrock/hooks/` | one gate (no pull request without a recorded review of its head commit) and helpers that inform (the working loop and stale notes at start, format and lint after an edit, earlier answers to repeated questions, auto-continue when switched on) |
| CLI | `plugins/bedrock/bin/bedrock` | day log and minutes, backlog, test and command wrappers with a machine lock, leak and code checks, knowledge base, call archive, retro numbers, night watchdog, doctor |
| Packs | `plugins/bedrock/packs/` | domain rule sets switched on per project: python, typescript, db, api-security, frontend, jobs, medical |
| Bench | `bench/` | a small app with seeded defects that measures the system; its answer key lives outside the repository |

## How a task goes

1. **Intake.** The request gets a risk level (R1 no logic, R2 ordinary code, R3 risky or new)
   and a priority (P0 to P3). P0 goes to an urgent path.
2. **Plan.** R2 and R3 get a plan with a checkable done-when, assumptions, files, named tests and
   tasks. A critic agent that did not see it being written reviews it.
3. **The owner's go.** One «го» covers the whole plan.
4. **Tasks.** One task is one commit with its own test, red before the change.
5. **Review.** Deterministic checks first, then a code review and a plan-compliance review;
   every real finding is fixed, imaginary ones are rejected with evidence; rounds until clean.
6. **Deliver.** Branch, PR, merge and deploy go on the owner's word. A user-visible change
   is checked live before it is called done.
7. **Close.** Minutes from the day log, the knowledge base updated, a plain report.

## Hooks

The hooks refuse one thing: `gh pr create` and `gh pr merge` without a review record for the
head commit. `bedrock review pass <branch> --agent <id>` writes that record only when a reviewer
agent of the same session finished after the branch's last commit; a later commit voids it.
Everything else is the session's own discipline and the owner's word in the conversation.
If bedrock itself cannot load, work goes on and only that gate refuses. The gate is a check
against forgetting, not against a session set on getting round it: it reads `gh pr create` and
`gh pr merge` as written (a `gh api` call or a gh alias passes), and it checks that a reviewer
finished after the last commit, not what that reviewer read. `BEDROCK_HOOKS=off` turns the
hooks off.

Agent runs are read from Claude Code's own transcripts: `bedrock agents` shows them by role,
model, day or project, and says how many transcripts it could not read.

## Folders

| Folder | What lives there |
|---|---|
| `~/projects-memory-bank/<project>/` | the knowledge base: decisions, architecture, failures, runbooks, handoffs, FAQ; a local git repository |
| `~/projects-days/<project>/` | day logs, block folders with plans and agent reports, the question log, the call archive |
| `~/.local/state/bedrock/` | session state, review records, code maps |
| `~/.config/bedrock/` | the owner's settings (`config.json`), the private leak-term list, the voice profile |

A project's own settings live in `<workspace>/.claude/bedrock.json` (commands, critical zones,
packs); `bedrock project check` validates them.

## Documentation

- `plugins/bedrock/docs/ru-guide.md`: the owner's guide, in Russian: what to say, the hooks, the
  night mode, folders, what to do when something is off.
- `plugins/bedrock/docs/cheatsheet.md`: one page; `folio cheatsheet.md` renders it as a PDF.

## Development

```
uvx pytest -p no:cacheprovider -q           # the suite
uvx ruff check . && uvx black --check .     # lint and format
python3 plugins/bedrock/scripts/skillcheck.py --root plugins/bedrock --strict
```

Python is standard library only. Every hook and script has tests for both what it refuses and
what it lets through. Skill texts follow the rules in the `writing` skill and are checked by
`skillcheck.py`.

## Licence

MIT, see `LICENSE`. Parts adapted from other MIT projects are listed in
`plugins/bedrock/NOTICE`.
