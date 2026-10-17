#!/usr/bin/env node
/**
 * contrast.mjs — the measurable-floor CONTRAST check, COMPUTED not eyeballed, BEFORE render.
 *
 * Why this exists (the layer-1 lesson): WCAG contrast is pure math on two colours, yet the
 * generator "eyeballs" it and the refined tinted-neutral / one-accent look systematically
 * undershoots 4.5:1 on secondary/label text — caught only late by axe at the gate, then
 * regenerated. This computes the floor at TOKEN-LOCK time (before a line of CSS is written), so a
 * bad palette is fixed up front instead of discovered after rendering. axe (in verify.mjs) stays
 * the render-time backstop; this is the cheap render-free pre-check.
 *
 * Floor: WCAG AA — 4.5:1 normal text, 3.0:1 large/UI. (Engine owns this; it never reaches the owner.)
 *
 * Commands:
 *   pair  <fg> <bg> [--large]     # one ratio + PASS/FAIL (hex #rgb/#rrggbb or rgb()/rgba())
 *   check <tokens.json> [--min N] # classify token colours, check fg×bg (4.5) and accent×bg (3.0); exit 1 on any fail
 *   selftest                      # guards the math + the classify/check path (zero-dep, CI-safe)
 * stdlib/node only.
 */
import { readFileSync, existsSync } from "node:fs";

const AA_TEXT = 4.5, AA_LARGE = 3.0;
const FG_RE = /ink|text|fg|foreground|body|head|title|label|dim|mut|secondary|caption|subtle|placeholder/i;
const BG_RE = /bg|background|base|surface|panel|card|canvas|paper|fill|sheet/i;
const ACCENT_RE = /accent|brand|primary|highlight|link|cta|action/i;

const srgbToLin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const luminance = (r, g, b) => 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);

function parseColor(s) {
  if (typeof s !== "string") return null;
  s = s.trim();
  let m = s.match(/^#([0-9a-f]{3})$/i);
  if (m) { const h = m[1]; return [0, 1, 2].map((i) => parseInt(h[i] + h[i], 16)); }
  m = s.match(/^#([0-9a-f]{6})$/i);
  if (m) { const h = m[1]; return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  m = s.match(/^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/i);
  if (m) return [+m[1], +m[2], +m[3]];
  return null;
}

function ratio(fg, bg) {
  const a = parseColor(fg), b = parseColor(bg);
  if (!a || !b) return null;
  const L1 = luminance(...a), L2 = luminance(...b);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
}
const r2 = (x) => Math.round(x * 100) / 100;

// flatten a tokens object to { dotted.path: "#hex" } for every parseable colour string
function colorLeaves(obj, prefix = "", out = {}) {
  if (obj && typeof obj === "object") {
    for (const k of Object.keys(obj)) colorLeaves(obj[k], prefix ? `${prefix}.${k}` : k, out);
  } else if (parseColor(obj)) {
    out[prefix] = obj;
  }
  return out;
}

function cmd_pair(fg, bg, large) {
  const ra = ratio(fg, bg);
  if (ra == null) { console.error("unparseable colour(s):", fg, bg); process.exit(2); }
  const floor = large ? AA_LARGE : AA_TEXT;
  const pass = ra >= floor;
  console.log(JSON.stringify({ fg, bg, ratio: r2(ra), floor, pass }, null, 2));
  process.exit(pass ? 0 : 1);
}

function checkTokens(colors, min) {
  const names = Object.keys(colors);
  const fgs = names.filter((n) => FG_RE.test(n) && !BG_RE.test(n));
  const bgs = names.filter((n) => BG_RE.test(n));
  const accents = names.filter((n) => ACCENT_RE.test(n));
  const fails = [];
  for (const f of fgs) for (const b of bgs) {
    const ra = ratio(colors[f], colors[b]);
    if (ra != null && ra < (min ?? AA_TEXT)) fails.push({ kind: "text", fg: f, bg: b, ratio: r2(ra), floor: min ?? AA_TEXT });
  }
  for (const a of accents) for (const b of bgs) {
    const ra = ratio(colors[a], colors[b]);
    if (ra != null && ra < AA_LARGE) fails.push({ kind: "accent/ui", fg: a, bg: b, ratio: r2(ra), floor: AA_LARGE });
  }
  return { fgs, bgs, accents, fails };
}

function cmd_check(file, min) {
  if (!existsSync(file)) { console.error("no such tokens file:", file); process.exit(2); }
  let json; try { json = JSON.parse(readFileSync(file, "utf8")); }
  catch (e) { console.error("bad JSON:", e.message); process.exit(2); }
  const colors = colorLeaves(json);
  const { fgs, bgs, accents, fails } = checkTokens(colors, min);
  if (!fgs.length || !bgs.length) {
    console.log(JSON.stringify({ note: "could not classify foreground/background token names — checked nothing; name them ink/text/dim & bg/surface for the floor check", colors: Object.keys(colors) }, null, 2));
    process.exit(0);
  }
  console.log(JSON.stringify({ checked: { foregrounds: fgs.length, backgrounds: bgs.length, accents: accents.length }, fails, clean: !fails.length, note: "AA floor: 4.5 text, 3.0 accent/UI. Fix the palette before building — this is layer-1, the engine's job, not the owner's." }, null, 2));
  process.exit(fails.length ? 1 : 0);
}

function selftest() {
  const approx = (a, b, t = 0.05) => Math.abs(a - b) <= t;
  let ok = true;
  const cases = [["#ffffff", "#000000", 21], ["#767676", "#ffffff", 4.54], ["#999999", "#ffffff", 2.85], ["#595959", "#ffffff", 7.0]];
  for (const [fg, bg, exp] of cases) {
    const got = ratio(fg, bg);
    if (!approx(got, exp, 0.06)) { console.error(`  math FAIL ${fg}/${bg}: got ${r2(got)} expected ~${exp}`); ok = false; }
  }
  // rgb() parsing + 3-digit hex
  if (!approx(ratio("rgb(255,255,255)", "#000"), 21, 0.1)) { console.error("  parse FAIL rgb()/#000"); ok = false; }
  // classify + check: a "good" palette is clean, a "bad" one (dim under 4.5) is flagged
  const good = checkTokens(colorLeaves({ colors: { bg: "#14130f", ink: "#efe9da", dim: "#a39d8c", accent: "#d8a43a" } }));
  if (good.fails.length) { console.error("  check FAIL: good palette flagged", good.fails); ok = false; }
  const bad = checkTokens(colorLeaves({ colors: { surface: "#ffffff", label: "#b3b3b3" } })); // ~2.6:1
  if (!bad.fails.length) { console.error("  check FAIL: bad palette (label on white) NOT flagged"); ok = false; }
  console.log(ok ? "contrast.mjs selftest: PASS" : "contrast.mjs selftest: FAIL");
  process.exit(ok ? 0 : 1);
}

const argv = process.argv.slice(2);
const large = argv.includes("--large");
const minI = argv.indexOf("--min");
const min = minI > -1 ? Number(argv[minI + 1]) : undefined;
const [cmd, a, b] = argv;
if (cmd === "pair") cmd_pair(a, b, large);
else if (cmd === "check") cmd_check(a, min);
else if (cmd === "selftest") selftest();
else { console.error("usage: contrast.mjs pair <fg> <bg> [--large] | check <tokens.json> [--min N] | selftest"); process.exit(2); }
