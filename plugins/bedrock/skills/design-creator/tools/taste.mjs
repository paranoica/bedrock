#!/usr/bin/env node
/**
 * taste.mjs — turn the owner's pairwise picks into a compounding taste model.
 *
 * "Ahuenny" is not objectively definable, so we define it operationally as *this
 * owner's revealed preference*: when they pick A over B (in the diverse best-of-N
 * of the work loop, or an explicit pair), log it. Over ~20–50 votes this yields:
 *   - an Elo rating per candidate (Bradley-Terry-style online comparison),
 *   - per-axis aggregates (does the owner lean high type-contrast? dense? etc.),
 *   - a set of WINNERS that serve as generator exemplars + critic anchors.
 *
 * It is advisory and never overrides the floor (a11y/perf/anti-slop/invariants).
 * Pairwise picking provably overcomes cold-start; this is the cold-start cure too.
 *
 * Commands:
 *   vote <winnerId> <loserId> [--family F] [--axes a,b,c]   # axes the winner won on
 *   rank   [--family F]                                     # Elo leaderboard
 *   anchors [--family F] [--n 3]                            # top winners (for generator/critic)
 *   axes                                                    # per-axis owner lean
 *
 * Store: $CLAUDE_DESIGN_DIR/.design/taste/votes.jsonl (default .design/taste/).
 * stdlib/node only.
 */
import { appendFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DIR = process.env.CLAUDE_DESIGN_DIR || ".design";
const LOG = `${DIR}/taste/votes.jsonl`;
const K = 24; // Elo K-factor (sparse data → keep it moving)

const AXES = ["type_contrast", "color_discipline", "density", "motion_intensity", "signature"];

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
function loadVotes() {
  if (!existsSync(LOG)) return [];
  return readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}
function vote(winner, loser) {
  if (!winner || !loser) { console.error("usage: vote <winnerId> <loserId> [--family F] [--axes a,b]"); process.exit(2); }
  const rec = { winner, loser, family: arg("family", "any"),
    axes: (arg("axes", "") || "").split(",").map(s => s.trim()).filter(Boolean),
    ts: Date.now() };
  mkdirSync(dirname(LOG), { recursive: true });
  appendFileSync(LOG, JSON.stringify(rec) + "\n");
  console.log(JSON.stringify({ recorded: rec }));
}
function elo(votes) {
  const R = {};
  const seed = id => (R[id] ??= 1000);
  for (const v of votes) {
    const ra = seed(v.winner), rb = seed(v.loser);
    const ea = 1 / (1 + 10 ** ((rb - ra) / 400));
    R[v.winner] = ra + K * (1 - ea);
    R[v.loser] = rb + K * (0 - (1 - ea));
  }
  return R;
}
function rank(family) {
  let votes = loadVotes();
  if (family && family !== "any") votes = votes.filter(v => v.family === family);
  const R = elo(votes);
  const n = {}; for (const v of votes) { n[v.winner] = (n[v.winner]||0)+1; n[v.loser] = (n[v.loser]||0)+1; }
  const board = Object.entries(R).sort((a, b) => b[1] - a[1])
    .map(([id, r]) => ({ id, rating: Math.round(r), comparisons: n[id] || 0 }));
  console.log(JSON.stringify({ family: family || "all", votes: votes.length, leaderboard: board,
    note: "Elo over pairwise owner picks. Need ~20–50 votes before trusting the order." }, null, 2));
}
function anchors(family, nn) {
  let votes = loadVotes();
  if (family && family !== "any") votes = votes.filter(v => v.family === family);
  const R = elo(votes);
  const top = Object.entries(R).sort((a, b) => b[1] - a[1]).slice(0, nn).map(([id]) => id);
  console.log(JSON.stringify({ family: family || "all", anchors: top,
    note: "Feed these owner-winners as generator exemplars and as the critic's Tier-3 pairwise anchor.",
    cold_start: votes.length < 8 }, null, 2));
}
function axes() {
  const votes = loadVotes();
  const tally = Object.fromEntries(AXES.map(a => [a, 0]));
  let withAxes = 0;
  for (const v of votes) for (const ax of (v.axes || [])) if (ax in tally) { tally[ax]++; withAxes++; }
  console.log(JSON.stringify({ votes: votes.length, votes_with_axis_annotation: withAxes,
    axis_win_counts: tally,
    note: "How often the owner's pick was the higher-X option. Bias the generator toward the leaders; advisory only." }, null, 2));
}

const [cmd, x, y] = process.argv.slice(2);
if (cmd === "vote") vote(x, y);
else if (cmd === "rank") rank(arg("family"));
else if (cmd === "anchors") anchors(arg("family"), +(arg("n", "3")));
else if (cmd === "axes") axes();
else { console.error("usage: taste.mjs vote <w> <l> [--family F] [--axes a,b] | rank [--family F] | anchors [--family F] [--n 3] | axes"); process.exit(2); }
