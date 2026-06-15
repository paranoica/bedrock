#!/usr/bin/env node
/**
 * spread.mjs — make structural diversity MECHANICAL, not hoped-for. (principles/diversity.md)
 *
 * The map (enumerable axes, grounded in the principle files):
 *   Category = page archetype  (page-architecture.md, 8)
 *   Type     = hook mechanism  (concept.md, 6)
 *   => 48 structural cells. Aesthetic family (aesthetic-families.md, ~14) is a character overlay.
 *
 * Commands:
 *   assign <brief> <N>                          # N DISTINCT cells, tail-biased, avoiding last-K used
 *   check  <archetype> <mechanism> [--family F] [--brief B]   # collision verdict + novelty percentile
 *   commit <archetype> <mechanism> --family F [--brief B] [--pin]  # record to ledger + log
 *   cells                                        # print the axis vocabularies
 *
 * State (per project, only when available):
 *   $CLAUDE_DESIGN_DIR/.design/ledger.json   { spread:[{archetype,mechanism,family,brief,ts}], pins:[{archetype,mechanism}] }
 *   $CLAUDE_DESIGN_DIR/.design/spread-log.jsonl  append-only {ts,brief,cell,family,novelty_pct,verdict}
 * stdlib/node only. Exit 0 except check-collision (exit 1) so a caller can gate.
 */
import { readFileSync, writeFileSync, appendFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const ARCHETYPES = [
  "classic-landing", "continuous-canvas", "editorial-longread", "index-directory",
  "horizontal-sideways", "split-two-track", "single-scene-focus", "conversation-reveal",
];
const MECHANISMS = [
  "scroll-morph", "cursor-pointer", "reframed-navigation",
  "living-system", "structural-typographic", "input-participation",
];
const FAMILIES = [
  "editorial-minimalism", "cinematic-dark", "warm-editorial", "terminal-core",
  "data-dense-pro", "playful-color", "glass-soft-futurism", "neon-brutalist",
  "swiss-international", "tactile-brutalism", "y2k", "organic-humanist",
  "editorial-print", "riso",
];
const K = 8;          // sameness window
const DIR = process.env.CLAUDE_DESIGN_DIR || ".design";
const LEDGER = `${DIR}/ledger.json`;
const LOG = `${DIR}/spread-log.jsonl`;

function arg(name, def = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i !== -1 && (name === "pin" || process.argv[i + 1]) ? (name === "pin" ? true : process.argv[i + 1]) : def;
}
function loadLedger() {
  if (!existsSync(LEDGER)) return { spread: [], pins: [] };
  try {
    const j = JSON.parse(readFileSync(LEDGER, "utf8"));
    return { spread: Array.isArray(j.spread) ? j.spread : [], pins: Array.isArray(j.pins) ? j.pins : [], _other: j };
  } catch { return { spread: [], pins: [] }; }
}
function saveLedger(l) {
  mkdirSync(dirname(LEDGER), { recursive: true });
  const base = l._other && typeof l._other === "object" ? l._other : {};
  writeFileSync(LEDGER, JSON.stringify({ ...base, spread: l.spread, pins: l.pins }, null, 2));
}
const cellKey = (a, m) => `${a}|${m}`;
const isPinned = (l, a, m) => l.pins.some(p => p.archetype === a && p.mechanism === m);
function distance(a1, m1, a2, m2) { return (a1 !== a2 ? 1 : 0) + (m1 !== m2 ? 1 : 0); }

// usage counts per cell (all-time, for novelty) and the last-K used cells (for collision)
function usage(l) {
  const counts = {};
  for (const a of ARCHETYPES) for (const m of MECHANISMS) counts[cellKey(a, m)] = 0;
  for (const e of l.spread) { const k = cellKey(e.archetype, e.mechanism); if (k in counts) counts[k]++; }
  const recent = l.spread.slice(-K).map(e => cellKey(e.archetype, e.mechanism));
  return { counts, recent };
}
// novelty percentile: fraction of the 48 cells that are used MORE than this one (higher = more novel)
function noveltyPct(counts, a, m) {
  const mine = counts[cellKey(a, m)] ?? 0;
  const all = Object.values(counts);
  const moreUsed = all.filter(c => c > mine).length;
  return Math.round((moreUsed / all.length) * 100);
}

function cmd_cells() {
  console.log(JSON.stringify({ archetypes: ARCHETYPES, mechanisms: MECHANISMS, families: FAMILIES,
    structural_cells: ARCHETYPES.length * MECHANISMS.length }, null, 2));
}

function cmd_assign(brief, n) {
  const N = Math.max(1, Math.min(parseInt(n || "3", 10) || 3, ARCHETYPES.length * MECHANISMS.length));
  const l = loadLedger();
  const { counts, recent } = usage(l);
  // candidate pool: all cells, scored by (under-use, not-recent, jitter); pick greedily maximizing spread
  const pool = [];
  for (const a of ARCHETYPES) for (const m of MECHANISMS) {
    const k = cellKey(a, m);
    pool.push({ archetype: a, mechanism: m, count: counts[k], recent: recent.includes(k), jitter: Math.random() });
  }
  pool.sort((x, y) => (x.recent - y.recent) || (x.count - y.count) || (x.jitter - y.jitter));
  const chosen = [];
  const usedArch = new Set(), usedMech = new Set();
  // Pass 1: strict Latin-square — no repeated archetype AND no repeated mechanism.
  for (const c of pool) {
    if (chosen.length >= N) break;
    if (!usedArch.has(c.archetype) && !usedMech.has(c.mechanism)) {
      chosen.push(c); usedArch.add(c.archetype); usedMech.add(c.mechanism);
    }
  }
  // Pass 2: relax to differ on at least one axis (distance >= 1) if still short.
  for (const c of pool) {
    if (chosen.length >= N) break;
    if (chosen.includes(c)) continue;
    const minDist = Math.min(...chosen.map(s => distance(s.archetype, s.mechanism, c.archetype, c.mechanism)));
    if (minDist >= 1) chosen.push(c);
  }
  // Pass 3: top up with anything left (only when N exceeds what spread allows).
  for (const c of pool) { if (chosen.length >= N) break; if (!chosen.includes(c)) chosen.push(c); }
  const family = [...FAMILIES].sort(() => Math.random() - 0.5);
  const out = chosen.slice(0, N).map((c, i) => ({
    candidate: i + 1, archetype: c.archetype, mechanism: c.mechanism,
    suggested_family: family[i % family.length], novelty_pct: noveltyPct(counts, c.archetype, c.mechanism),
  }));
  const pairwise = [];
  for (let i = 0; i < out.length; i++) for (let j = i + 1; j < out.length; j++)
    pairwise.push(distance(out[i].archetype, out[i].mechanism, out[j].archetype, out[j].mechanism));
  console.log(JSON.stringify({
    brief: brief || "unspecified", n: N, cells: out,
    min_pairwise_distance: pairwise.length ? Math.min(...pairwise) : 2,
    note: "Generate each candidate INTO its assigned cell. min distance 2 = fully spread (differ on both axes).",
  }, null, 2));
}

function cmd_check(a, m, brief) {
  if (!ARCHETYPES.includes(a) || !MECHANISMS.includes(m)) {
    console.error(`unknown cell. archetypes: ${ARCHETYPES.join(",")} | mechanisms: ${MECHANISMS.join(",")}`);
    process.exit(2);
  }
  const l = loadLedger();
  const { counts, recent } = usage(l);
  const pinned = isPinned(l, a, m);
  const collision = recent.includes(cellKey(a, m));
  const nov = noveltyPct(counts, a, m);
  let verdict, note;
  if (pinned) { verdict = "OK_PINNED"; note = "pinned favourite — deliberate consistency, exempt from the sameness check."; }
  else if (collision) { verdict = "REROLL"; note = `exact cell reused within the last ${K} builds without a pin — pick a different archetype AND/OR mechanism, or justify the repeat explicitly.`; }
  else { verdict = "OK"; note = `cell not used in the last ${K} builds; novelty ${nov}th percentile.`; }
  console.log(JSON.stringify({ cell: cellKey(a, m), family: arg("family"), brief: brief || "all",
    verdict, novelty_pct: nov, pinned, collision, window: K, note }, null, 2));
  process.exit(verdict === "REROLL" ? 1 : 0);
}

function cmd_commit(a, m, brief) {
  if (!ARCHETYPES.includes(a) || !MECHANISMS.includes(m)) {
    console.error(`unknown cell. archetypes: ${ARCHETYPES.join(",")} | mechanisms: ${MECHANISMS.join(",")}`);
    process.exit(2);
  }
  const l = loadLedger();
  const { counts } = usage(l);
  const family = arg("family") || "unspecified";
  const pin = arg("pin", false);
  const nov = noveltyPct(counts, a, m);
  const entry = { archetype: a, mechanism: m, family, brief: brief || "all", ts: Date.now() };
  l.spread.push(entry);
  if (pin && !isPinned(l, a, m)) l.pins.push({ archetype: a, mechanism: m });
  saveLedger(l);
  mkdirSync(dirname(LOG), { recursive: true });
  appendFileSync(LOG, JSON.stringify({ ...entry, cell: cellKey(a, m), novelty_pct: nov, pinned: pin }) + "\n");
  console.log(JSON.stringify({ committed: entry, cell: cellKey(a, m), novelty_pct: nov, pinned: !!pin,
    note: pin ? "recorded + pinned (exempt from future sameness checks)." : "recorded to ledger + spread-log." }, null, 2));
}

const [cmd, x, y] = process.argv.slice(2);
if (cmd === "cells") cmd_cells();
else if (cmd === "assign") cmd_assign(x, y);
else if (cmd === "check") cmd_check(x, y, arg("brief"));
else if (cmd === "commit") cmd_commit(x, y, arg("brief"));
else { console.error("usage: spread.mjs assign <brief> <N> | check <archetype> <mechanism> [--family F] [--brief B] | commit <archetype> <mechanism> --family F [--brief B] [--pin] | cells"); process.exit(2); }
