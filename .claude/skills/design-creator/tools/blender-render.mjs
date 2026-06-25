#!/usr/bin/env node
/**
 * blender-render.mjs — the baked-3D harness: run a parametric recipe headless and emit a
 * hash-bound verdict the gate/critic read instead of self-attesting. The offline-render sibling
 * of verify.mjs (browser render → web). Node *orchestrates* Blender (as verify.mjs orchestrates
 * Playwright); the bpy recipe + stage.py do the in-engine work (as in-page JS does in the browser).
 *
 * It does NOT judge taste. It measures what a machine can — did anything render (alpha coverage),
 * is it not a flat black/empty fill (luminance stddev), is the mesh within the poly budget, is the
 * GLB structurally valid (when a validator is present) — and it hands the LOOK-at-the-render
 * obligation to the critic (visual_required), which compares against a 3D exemplar because the
 * model's spatial/material taste is its weakest axis (see principles/3d-baked.md).
 *
 * Verdict tiers mirror verify.mjs on purpose:
 *   measured   — script decides, binary (render_succeeded, not_black, poly_budget)
 *   visual     — the critic must LOOK at render.png and compare to the 3D exemplar
 *   advisory   — non-blocking (render time; GLB unverified when no validator)
 *   unverified — no Blender available → labelled, never silently passed (exit 3)
 *
 * Freshness binding: scene_hash = sha256(recipe + stage.py + canonical params). A report whose
 * hash != the current inputs is stale and the gate must reject it (no "I rendered it earlier").
 *
 * Usage:
 *   node blender-render.mjs <recipe.py> [--out .design/3d] [--params '<json>']
 *     [--blender blender] [--poly-budget 250000]
 * Exit codes: 0 all measured checks pass · 1 a measured check failed · 3 no Blender.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const THRESH = { MIN_COVERAGE: 0.015, MIN_STDDEV: 0.008, POLY_BUDGET: 250000 };

function arg(flag, def) {
  const i = process.argv.indexOf(flag);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const recipeArg = process.argv[2];
if (!recipeArg || recipeArg.startsWith("--")) {
  console.error("usage: node blender-render.mjs <recipe.py> [--out dir] [--params json] [--blender bin] [--poly-budget n]");
  process.exit(2);
}
const recipe = resolve(recipeArg);
if (!existsSync(recipe)) { console.error("recipe not found: " + recipe); process.exit(2); }
const outDir = arg("--out", ".design/3d");
const paramsRaw = arg("--params", "{}");
const blenderBin = arg("--blender", "blender");
const polyBudget = parseInt(arg("--poly-budget", String(THRESH.POLY_BUDGET)), 10);

let params;
try { params = JSON.parse(paramsRaw); } catch (e) {
  console.error("--params is not valid JSON: " + e.message); process.exit(2);
}

// Freshness binding: hash recipe + the stager lib + canonical params.
const libPath = resolve(dirname(recipe), "../lib/stage.py");
const hashSrc = createHash("sha256");
hashSrc.update(readFileSync(recipe));
if (existsSync(libPath)) hashSrc.update(readFileSync(libPath));
hashSrc.update(JSON.stringify(sortKeys(params)));
const sceneHash = "blend:" + hashSrc.digest("hex").slice(0, 16);

mkdirSync(outDir, { recursive: true });

function sortKeys(o) {
  if (o === null || typeof o !== "object" || Array.isArray(o)) return o;
  return Object.keys(o).sort().reduce((a, k) => ((a[k] = sortKeys(o[k])), a), {});
}

function noBlenderReport(reason) {
  return {
    scene_hash: sceneHash, blender: false, generated_at: new Date().toISOString(), reason,
    recipe, params,
    summary: {
      verdict: "UNVERIFIED", measured_pass: 0, measured_fail: 0, unverified: 1,
      note: "No Blender: the baked render was NOT produced — checks are unverified, not passed. " +
            "The gate must label the 3D asset 'requires render' (or fall back to in-browser R3F), never green.",
    },
    measured: [], visual_required: [], advisory: [],
    unverified: ["render, not_black, poly_budget — requires Blender (" + reason + ")"],
    outputs: {},
  };
}

// ---- honest fallback: no Blender on PATH -> label, don't fake (mirror verify's no-browser) ----
const probe = spawnSync(blenderBin, ["--version"], { encoding: "utf8" });
if (probe.error) {
  const report = noBlenderReport(`'${blenderBin}' not runnable: ${probe.error.code || probe.error.message}`);
  writeFileSync(`${outDir}/render-report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary, null, 2));
  process.exit(3);
}
const blenderVersion = (probe.stdout || "").split("\n")[0].trim();

// ---- run the recipe headless ----
const run = spawnSync(
  blenderBin,
  ["-b", "--factory-startup", "-noaudio", "-P", recipe, "--", "--out", outDir, "--params", JSON.stringify(params)],
  { encoding: "utf8", timeout: 600000 },
);
const log = (run.stdout || "") + "\n----- stderr -----\n" + (run.stderr || "");
writeFileSync(`${outDir}/blender.log`, log);

const measured = [];
const visualRequired = [];
const advisory = [];
const outputs = {};

if (run.status !== 0) {
  // Render failed inside Blender — surface the tail, this is a hard measured fail.
  const tail = log.trim().split("\n").slice(-12).join("\n");
  measured.push({ check: "render_succeeded", pass: false, detail: `blender exit ${run.status}; log tail:\n${tail}` });
} else {
  const statsPath = `${outDir}/render-stats.json`;
  if (!existsSync(statsPath)) {
    measured.push({ check: "render_succeeded", pass: false, detail: "blender exited 0 but wrote no render-stats.json (recipe did not reach stage.finish)" });
  } else {
    const stats = JSON.parse(readFileSync(statsPath, "utf8"));
    const pngOk = stats.png && existsSync(stats.png);
    outputs.png = pngOk ? stats.png : null;
    outputs.glb = stats.glb || null;

    measured.push({ check: "render_succeeded", pass: !!pngOk, detail: pngOk ? `wrote ${stats.png} (${stats.resolution?.join("x")})` : "render.png missing" });

    // not_black/empty: something rendered (coverage) AND it has tonal variation (not a flat fill)
    const notBlack = stats.alpha_coverage >= THRESH.MIN_COVERAGE && stats.lum_stddev >= THRESH.MIN_STDDEV;
    measured.push({
      check: "not_black", pass: notBlack,
      detail: `alpha_coverage ${stats.alpha_coverage?.toFixed(3)} (≥${THRESH.MIN_COVERAGE}), ` +
              `lum_stddev ${stats.lum_stddev?.toFixed(3)} (≥${THRESH.MIN_STDDEV}), lum_mean ${stats.lum_mean?.toFixed(3)}`,
    });

    measured.push({
      check: "poly_budget", pass: stats.poly_count <= polyBudget,
      detail: `${stats.poly_count} polys (budget ${polyBudget}) — web ships light; bake/decimate if over`,
    });

    advisory.push({ check: "render_time", advisory: true, pass: true, detail: `${stats.render_seconds}s on ${params.device || "CPU"} @ ${stats.resolution?.join("x")} (preview fast; raise samples/res for ship)` });

    // loop mode: a seamless webm spin (non-interactive background loop)
    if (stats.video) {
      outputs.webm = stats.video.webm || null;
      const vOk = stats.video.webm && existsSync(stats.video.webm) && stats.video.bytes > 1024;
      measured.push({
        check: "video_present", pass: !!vOk,
        detail: vOk
          ? `${stats.video.webm} (${stats.video.frames}f @ ${stats.video.fps}fps = ${stats.video.duration_s}s, ${Math.round(stats.video.bytes / 1024)}KB, ${stats.video.encode_seconds}s encode)`
          : "loop mode set but no usable webm produced — likely a VP9/ffmpeg issue in this Blender build (see blender.log)",
      });
    }

    // GLB structural validity — honest degrade when no validator is installed
    if (stats.glb) {
      const v = validateGlb(stats.glb);
      if (v.ran) measured.push({ check: "glb_valid", pass: v.pass, detail: v.detail });
      else advisory.push({ check: "glb_valid", advisory: true, pass: true, detail: v.detail });
    } else if (params.glb) {
      measured.push({ check: "glb_valid", pass: false, detail: "params.glb set but no GLB was exported" });
    }
  }
}

// the render PNG carries a LOOK obligation the harness cannot discharge (mirror verify's visual tier)
if (outputs.png) {
  visualRequired.push({
    check: "visual_3d_qa",
    why: "LOOK at render.png and judge against a 3D exemplar (references/3d-render-exemplar.md), NOT in a vacuum — " +
         "lighting believable (not flat default-clay); composition/framing intentional; the material reads as intended " +
         "(glass refracts, metal has something to reflect, emissive glows); silhouette legible; no fireflies/noise/clipping. " +
         "The model's 3D/material taste is its weakest axis — compare to the exemplar; if low-confidence, return UNVERIFIED " +
         "and recommend an owner vote rather than forcing a verdict.",
  });
}

function validateGlb(glbPath) {
  for (const bin of ["gltf-validator", "gltf_validator"]) {
    const r = spawnSync(bin, [glbPath], { encoding: "utf8" });
    if (r.error) continue; // not installed under this name; try the next
    const pass = r.status === 0;
    return { ran: true, pass, detail: pass ? `${bin}: valid GLB` : `${bin}: validation errors (exit ${r.status}) — see ${glbPath}` };
  }
  return {
    ran: false,
    detail: "GLB exported but NOT validated: no gltf-validator on PATH. Install the Khronos glTF-Validator to gate this; " +
            "until then GLB structural validity is UNVERIFIED (advisory).",
  };
}

const fails = measured.filter((m) => !m.pass);
const report = {
  scene_hash: sceneHash,
  blender: true,
  blender_version: blenderVersion,
  generated_at: new Date().toISOString(),
  recipe,
  params,
  summary: {
    verdict: fails.length ? "MEASURED_FAIL" : "MEASURED_PASS",
    measured_pass: measured.length - fails.length,
    measured_fail: fails.length,
    visual_checks_required: visualRequired.length,
    advisory_count: advisory.length,
    note: "MEASURED_PASS means only the measurable tier is green (render produced, not black, within poly budget). " +
          "The asset is NOT cleared until the critic does visual_3d_qa against the render PNG + 3D exemplar. " +
          "advisory[] are non-blocking signals (render time, and GLB validity when no validator is installed).",
  },
  blocking_failures: fails,
  measured,
  visual_required: visualRequired,
  advisory,
  outputs,
  log: `${outDir}/blender.log`,
};
writeFileSync(`${outDir}/render-report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report.summary, null, 2));
process.exit(fails.length ? 1 : 0);
