#!/usr/bin/env node
/**
 * diversity.mjs — measure whether outputs are structurally DIVERSE, not just "different".
 * Companion to principles/diversity.md + tools/spread.mjs. Without this we can't tell whether
 * the axis-spread machinery actually spreads outputs or we just believe it does.
 *
 * A fingerprint is { archetype, mechanism, family }. Structural distance between two:
 *   (archetype differ ?1:0) + (mechanism differ ?1:0)   -> 0..2   (family adds a soft +0.5)
 *
 * Commands:
 *   score <fingerprints.json>   # array of fingerprints -> min/mean pairwise distance + verdict
 *   score --log                 # read fingerprints from $CLAUDE_DESIGN_DIR/.design/spread-log.jsonl
 *   selftest                    # prove the metric flags a CLUSTERED set and passes a SPREAD set
 *
 * Pass rule: no exact-cell duplicate among distinct candidates, mean structural distance >= 1.0,
 * min structural distance >= 1. Exit non-zero on fail (so it can gate in a suite).
 */
import { readFileSync, existsSync } from "node:fs";

const DIR = process.env.CLAUDE_DESIGN_DIR || ".design";
const LOG = `${DIR}/spread-log.jsonl`;

function dist(a, b) {
  let d = (a.archetype !== b.archetype ? 1 : 0) + (a.mechanism !== b.mechanism ? 1 : 0);
  if ((a.family || "") !== (b.family || "")) d += 0.5;
  return d;
}
function analyse(fps) {
  if (fps.length < 2) return { n: fps.length, note: "need >=2 fingerprints to measure spread" };
  const pair = [];
  let dupes = 0;
  for (let i = 0; i < fps.length; i++) for (let j = i + 1; j < fps.length; j++) {
    const d = dist(fps[i], fps[j]);
    pair.push(d);
    if (fps[i].archetype === fps[j].archetype && fps[i].mechanism === fps[j].mechanism) dupes++;
  }
  const min = Math.min(...pair), mean = pair.reduce((a, b) => a + b, 0) / pair.length;
  const cells = new Set(fps.map(f => `${f.archetype}|${f.mechanism}`));
  const fams = new Set(fps.map(f => f.family || ""));
  const pass = dupes === 0 && mean >= 1.0 && min >= 1;
  return {
    n: fps.length, distinct_cells: cells.size, distinct_families: fams.size,
    exact_cell_dupes: dupes, min_distance: +min.toFixed(2), mean_distance: +mean.toFixed(2),
    verdict: pass ? "PASS" : "CLUSTERED",
    note: pass ? "structurally spread — no cell collisions, healthy pairwise distance."
               : `clustering detected (dupes=${dupes}, min=${min}, mean=${mean.toFixed(2)}). Re-assign cells via tools/spread.mjs.`,
  };
}

function readLog() {
  if (!existsSync(LOG)) { console.error(`no spread-log at ${LOG}`); process.exit(2); }
  return readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse)
    .map(e => ({ archetype: e.archetype, mechanism: e.mechanism, family: e.family }));
}

function cmd_score(src) {
  let fps;
  if (src === "--log") fps = readLog();
  else { if (!src || !existsSync(src)) { console.error("usage: diversity.mjs score <fingerprints.json> | score --log"); process.exit(2); } fps = JSON.parse(readFileSync(src, "utf8")); }
  const r = analyse(fps);
  console.log(JSON.stringify(r, null, 2));
  process.exit(r.verdict === "PASS" ? 0 : 1);
}

function cmd_selftest() {
  // CLUSTERED: every output the same cell (the failure the eval must catch).
  const clustered = Array.from({ length: 4 }, () => ({ archetype: "classic-landing", mechanism: "scroll-morph", family: "cinematic-dark" }));
  // SPREAD: a Latin-square set (what tools/spread.mjs assign produces).
  const spread = [
    { archetype: "index-directory", mechanism: "scroll-morph", family: "editorial-minimalism" },
    { archetype: "conversation-reveal", mechanism: "cursor-pointer", family: "playful-color" },
    { archetype: "split-two-track", mechanism: "living-system", family: "cinematic-dark" },
    { archetype: "single-scene-focus", mechanism: "structural-typographic", family: "warm-editorial" },
  ];
  const c = analyse(clustered), s = analyse(spread);
  const ok = c.verdict === "CLUSTERED" && s.verdict === "PASS";
  console.log(JSON.stringify({
    clustered_set: { verdict: c.verdict, min: c.min_distance, mean: c.mean_distance, dupes: c.exact_cell_dupes },
    spread_set: { verdict: s.verdict, min: s.min_distance, mean: s.mean_distance, dupes: s.exact_cell_dupes },
    selftest: ok ? "PASS — metric flags clustering and passes spread." : "FAIL — metric does not distinguish clustered from spread.",
  }, null, 2));
  process.exit(ok ? 0 : 1);
}

const [cmd, x] = process.argv.slice(2);
if (cmd === "score") cmd_score(x);
else if (cmd === "selftest") cmd_selftest();
else { console.error("usage: diversity.mjs score <fingerprints.json> | score --log | selftest"); process.exit(2); }
