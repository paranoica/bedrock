# Bench

A small document search with known defects, used to measure the system (D010, D061): which
model finds what, at what cost, and whether a change to bedrock made things better or worse.

- `app/`: Python. Load, chunk, index and search documents (`python -m docsearch.cli`).
- `web/`: TypeScript. Highlight the query in a result snippet (`node --test`).
- `tasks/`: an inventory question set, an implementation task, and a plan to criticise.

Its tests pass. The defects are the ones the tests do not catch.

## The answer key
The key lists every seeded defect, the inventory answers, the hidden acceptance test of the
task and the flaws planted in the plan. It lives outside this repository, at the path in
`.claude/bedrock.json` (`bench.answer_key`), and the guard hooks refuse any agent read of it.
A run is scored against the key by the owner's session, never by an agent.

## Running it
Copy `app/` and `web/` into a fresh folder, open Claude Code there with the plugin enabled,
and give it one of the tasks. `bench/eval.sh` does this for you: it copies the cases from the
key folder into the plugin for the run and removes them afterwards. While a run lasts the
graders, and so the answers, sit inside the plugin folder: run it on a machine where nothing
else reads that folder.
