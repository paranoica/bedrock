#!/usr/bin/env node
/**
 * tournament.mjs — the eval quality loop. After any change to a MUSTHAVE rule, an
 * invariant, the gate, or the anti-slop catalog, re-generate the golden-brief
 * outputs and run a pairwise tournament: new outputs vs the prior champion vs the
 * reference exemplars. Votes come from the critic ensemble (on contested pairs, the
 * owner). Elo gives a ranking; the REGRESSION GUARD blocks a change that doesn't
 * actually improve — "different" is not "better".
 *
 * This stops the classic failure: you edit a rule and the output becomes merely
 * *other*, not better, and nobody notices because there was no champion to beat.
 *
 * Commands:
 *   match <winnerId> <loserId> [--brief B]        # record one pairwise result
 *   standings [--brief B]                          # Elo leaderboard for a brief (or all)
 *   champion  [--brief B]                          # current top id
 *   regression <newId> <prevChampionId> [--brief B]# did new beat prev? -> pass/block
 *
 * Store: $CLAUDE_DESIGN_DIR/.design/evals/matches.jsonl
 * stdlib/node only.
 */
import { appendFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DIR = process.env.CLAUDE_DESIGN_DIR || ".design";
const LOG = `${DIR}/evals/matches.jsonl`;
const K = 24;

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
function load() {
  if (!existsSync(LOG)) return [];
  return readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}
function elo(matches) {
  const R = {}; const seed = id => (R[id] ??= 1000);
  for (const m of matches) {
    const ra = seed(m.winner), rb = seed(m.loser);
    const ea = 1 / (1 + 10 ** ((rb - ra) / 400));
    R[m.winner] = ra + K * (1 - ea);
    R[m.loser] = rb - K * (1 - ea);
  }
  return R;
}
function filt(brief) { let m = load(); if (brief) m = m.filter(x => x.brief === brief); return m; }

function match(w, l) {
  if (!w || !l) { console.error("usage: match <winnerId> <loserId> [--brief B]"); process.exit(2); }
  const rec = { winner: w, loser: l, brief: arg("brief", "all"), ts: Date.now() };
  mkdirSync(dirname(LOG), { recursive: true });
  appendFileSync(LOG, JSON.stringify(rec) + "\n");
  console.log(JSON.stringify({ recorded: rec }));
}
function standings(brief) {
  const R = elo(filt(brief));
  const board = Object.entries(R).sort((a, b) => b[1] - a[1]).map(([id, r]) => ({ id, rating: Math.round(r) }));
  console.log(JSON.stringify({ brief: brief || "all", matches: filt(brief).length, standings: board }, null, 2));
}
function champion(brief) {
  const R = elo(filt(brief));
  const top = Object.entries(R).sort((a, b) => b[1] - a[1])[0];
  console.log(JSON.stringify({ brief: brief || "all", champion: top ? top[0] : null,
    rating: top ? Math.round(top[1]) : null }, null, 2));
}
function regression(neu, prev, brief) {
  if (!neu || !prev) { console.error("usage: regression <newId> <prevChampionId> [--brief B]"); process.exit(2); }
  const R = elo(filt(brief));
  const rn = R[neu], rp = R[prev];
  if (rn === undefined || rp === undefined) {
    console.log(JSON.stringify({ verdict: "INSUFFICIENT_DATA",
      note: `need head-to-head matches for both ${neu} and ${prev} under brief '${brief||"all"}'`,
      have: { [neu]: rn ?? null, [prev]: rp ?? null } }, null, 2));
    process.exit(0);
  }
  const beats = rn > rp;
  console.log(JSON.stringify({
    brief: brief || "all", new: { id: neu, rating: Math.round(rn) }, prev_champion: { id: prev, rating: Math.round(rp) },
    verdict: beats ? "PASS" : "REGRESSION_BLOCK",
    note: beats ? "new champion beats prior — the change is an improvement, ship it."
                : "new output does NOT beat the prior champion — the change made it different, not better. BLOCK and rework.",
  }, null, 2));
  process.exit(beats ? 0 : 1);
}

const [cmd, x, y] = process.argv.slice(2);
if (cmd === "match") match(x, y);
else if (cmd === "standings") standings(arg("brief"));
else if (cmd === "champion") champion(arg("brief"));
else if (cmd === "regression") regression(x, y, arg("brief"));
else { console.error("usage: tournament.mjs match <w> <l> [--brief B] | standings [--brief B] | champion [--brief B] | regression <new> <prev> [--brief B]"); process.exit(2); }
