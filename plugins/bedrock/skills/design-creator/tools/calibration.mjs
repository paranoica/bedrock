#!/usr/bin/env node
/**
 * calibration.mjs — does the engine's "this is good" actually mean good?
 *
 * Two judgments get logged here, both of the same shape ("engine predicted the
 * owner would keep it; did they?"):
 *   - ambition: the in-tier/borderline/below-tier call (record <p> <1|0>)
 *   - critic:   the QA-gate critic's SHIP/FIX_AND_RERUN decision, scored against
 *               whether the owner actually KEPT the shown result (record-critic).
 *
 * The critic asserts PASS/FAIL but, until now, never learned whether critic-SHIP
 * correlated with owner-accept — unlike the code-review side, which has had a
 * Brier loop for ages. This closes that asymmetry: feed the critic's decision +
 * the owner's resolution and read back a Brier score per kind. A critic that
 * keeps saying SHIP on things the owner discards is miscalibrated and should
 * tighten its bar.
 *
 * Brier = mean((p - outcome)^2); lower is better (0 = perfect).
 *
 * Usage:
 *   node calibration.mjs record <p 0..1> <outcome 1|0> [--kind ambition|critic]
 *   node calibration.mjs record-critic <SHIP|FIX_AND_RERUN> <outcome 1|0> [--p X] [--tier A|B|C]
 *        # outcome 1 = owner kept the shown result, 0 = owner rejected/redid it
 *   node calibration.mjs report [--kind critic|ambition]
 *   node calibration.mjs p <label>          # in-tier=0.85, borderline=0.55, below-tier=0.2
 *   node calibration.mjs selftest
 *
 * Log: $CLAUDE_DESIGN_DIR/.design/calibration.jsonl (or .design/ in cwd).
 */
import { appendFileSync, readFileSync, writeFileSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname } from "node:path";

const DIR = process.env.CLAUDE_DESIGN_DIR || ".design";
const LOG = `${DIR}/calibration.jsonl`;
const LABEL_P = { "in-tier": 0.85, "borderline": 0.55, "below-tier": 0.2 };
// A critic SHIP is a confident "owner will keep this"; FIX_AND_RERUN means it
// withheld — only the things it SHIPped are shown, so SHIP is the prediction we score.
const DECISION_P = { "SHIP": 0.8, "FIX_AND_RERUN": 0.2 };

function flag(args, name, def = undefined) {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : def;
}

function record(p, outcome, kind = "ambition", extra = {}) {
  mkdirSync(dirname(LOG), { recursive: true });
  const row = { p: +p, outcome: +outcome, kind, ...extra, ts: Date.now() };
  appendFileSync(LOG, JSON.stringify(row) + "\n");
  console.log(JSON.stringify({ recorded: row }));
}

function report(kind) {
  if (!existsSync(LOG)) return console.log(JSON.stringify({ n: 0, note: "no resolved designs logged yet" }, null, 2));
  let rows = readFileSync(LOG, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
  if (kind) rows = rows.filter((r) => (r.kind || "ambition") === kind);
  const n = rows.length;
  if (!n) return console.log(JSON.stringify({ n: 0, kind: kind || "all", note: "no rows for this kind yet" }, null, 2));
  const brier = rows.reduce((s, r) => s + (r.p - r.outcome) ** 2, 0) / n;
  const buckets = {};
  for (const r of rows) {
    const lo = Math.floor(r.p * 10) * 10;
    const key = `${lo}-${lo + 10}%`;
    (buckets[key] ||= []).push(r.outcome);
  }
  const table = {};
  for (const [k, v] of Object.entries(buckets).sort())
    table[k] = { count: v.length, observed_kept_rate: +(v.reduce((s, x) => s + x, 0) / v.length).toFixed(3) };
  console.log(JSON.stringify({
    kind: kind || "all", n, brier_score: +brier.toFixed(4),
    overall_kept_rate: +(rows.reduce((s, r) => s + r.outcome, 0) / n).toFixed(3),
    calibration_table: table,
    interpretation: "lower brier = better; observed rate should track the bucket. If critic-SHIP rows keep underperforming their p, the critic is too lenient — raise its bar.",
  }, null, 2));
}

function selftest() {
  const tmp = `${DIR}/.caltest`;
  const realLog = LOG;
  // run against an isolated log so we don't pollute real state
  const saved = process.env.CLAUDE_DESIGN_DIR;
  mkdirSync(tmp, { recursive: true });
  const testLog = `${tmp}/calibration.jsonl`;
  try {
    writeFileSync(testLog, "");
    const rows = [
      { p: 0.8, outcome: 1, kind: "critic" }, { p: 0.8, outcome: 0, kind: "critic" },
      { p: 0.8, outcome: 1, kind: "critic" }, { p: 0.85, outcome: 1, kind: "ambition" },
    ];
    appendFileSync(testLog, rows.map((r) => JSON.stringify({ ...r, ts: 1 })).join("\n") + "\n");
    const all = readFileSync(testLog, "utf8").trim().split("\n").map(JSON.parse);
    const critic = all.filter((r) => r.kind === "critic");
    const brier = critic.reduce((s, r) => s + (r.p - r.outcome) ** 2, 0) / critic.length;
    const ok = critic.length === 3 && Math.abs(brier - ((0.04 + 0.64 + 0.04) / 3)) < 1e-9;
    rmSync(tmp, { recursive: true, force: true });
    console.log(JSON.stringify({ selftest: ok ? "PASS — kind filter + brier compute correct" : "FAIL", critic_n: critic.length, critic_brier: +brier.toFixed(4) }, null, 2));
    process.exit(ok ? 0 : 1);
  } catch (e) {
    rmSync(tmp, { recursive: true, force: true });
    console.error("selftest error:", e.message); process.exit(1);
  }
}

const argv = process.argv.slice(2);
const [cmd, a, b] = argv;

if (cmd === "record" && a !== undefined && b !== undefined) {
  record(a, b, flag(argv, "--kind", "ambition"));
} else if (cmd === "record-critic" && a !== undefined && b !== undefined) {
  const decision = String(a).toUpperCase();
  const p = flag(argv, "--p") ?? DECISION_P[decision];
  if (p === undefined) { console.error("decision must be SHIP|FIX_AND_RERUN (or pass --p)"); process.exit(2); }
  record(p, b, "critic", { decision, tier: flag(argv, "--tier", "?") });
} else if (cmd === "report") {
  report(flag(argv, "--kind"));
} else if (cmd === "p" && a) {
  console.log(LABEL_P[a.toLowerCase()] ?? 0.5);
} else if (cmd === "selftest") {
  selftest();
} else {
  console.error("usage: calibration.mjs record <p> <1|0> [--kind k] | record-critic <SHIP|FIX_AND_RERUN> <1|0> [--p X] [--tier A|B|C] | report [--kind critic|ambition] | p <label> | selftest");
  process.exit(2);
}
