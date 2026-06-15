#!/usr/bin/env node
/**
 * motion.mjs — render-backed regression for the verify.mjs motion pass (M1–M4).
 *
 * Runs verify.mjs against three fixtures and asserts the verdicts that prove the pass has teeth:
 *   - animated (respects reduced-motion) → motion_non_inert PASS, reduced_motion_respected PASS
 *   - inert landing                      → motion_non_inert FAIL
 *   - animates but ignores reduced-motion → motion_non_inert PASS, reduced_motion_respected FAIL
 *
 * Self-skips (exit 0) when no browser is available — same honesty contract as the gate it guards
 * (browserless CI labels render checks "requires render", it does not fake them). Run after any
 * edit to the motion thresholds or the scroll/measure logic in verify.mjs.
 */
import { execFileSync } from "node:child_process";
import { readFileSync, mkdtempSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const VERIFY = resolve(HERE, "..", "tools", "verify.mjs");
const FX = resolve(HERE, "motion-fixtures");

function run(file) {
  const out = mkdtempSync(join(tmpdir(), "motion-eval-"));
  try {
    execFileSync("node", [VERIFY, resolve(FX, file), "--out", out, "--deliverable", "landing"],
      { stdio: "ignore" });
  } catch {
    /* exit 1 (measured fail) is expected for the inert/noreduced fixtures — read the report anyway */
  }
  const rp = join(out, "verify-report.json");
  if (!existsSync(rp)) throw new Error("no verify-report.json produced for " + file);
  return JSON.parse(readFileSync(rp, "utf8"));
}

const verdict = (report, check) => {
  const m = (report.measured || []).find((x) => x.check === check);
  return m ? m.pass : null; // null = check absent from the report
};

let fail = 0;
const ok = (name, cond) => { if (cond) console.log("  ok:", name); else { console.error("  FAIL:", name); fail = 1; } };

// browser gate: probe with one fixture; if no browser, skip the whole eval cleanly
const animated = run("motion-animated.html");
if (animated.browser === false) {
  console.log("  skip: no browser (browserless CI) — the motion pass is render-backed");
  process.exit(0);
}

ok("animated: motion_non_inert PASS", verdict(animated, "motion_non_inert") === true);
ok("animated: reduced_motion_respected PASS", verdict(animated, "reduced_motion_respected") === true);
ok("animated: scroll_jank PASS", verdict(animated, "scroll_jank") === true);

const inert = run("motion-inert.html");
ok("inert: motion_non_inert FAIL", verdict(inert, "motion_non_inert") === false);

const noreduced = run("motion-noreduced.html");
ok("noreduced: motion_non_inert PASS", verdict(noreduced, "motion_non_inert") === true);
ok("noreduced: reduced_motion_respected FAIL", verdict(noreduced, "reduced_motion_respected") === false);

console.log(fail ? "\nMOTION EVAL: FAIL" : "\nMOTION EVAL: PASS");
process.exit(fail);
