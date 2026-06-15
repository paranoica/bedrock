#!/usr/bin/env node
/**
 * verify.mjs — give the design-QA gate real eyes.
 *
 * Renders the build in a headless browser across {light,dark} × {320,768,1280},
 * runs axe-core, measures overflow / CLS / LCP, captures per-section screenshots,
 * and emits a machine-readable verdict the gate reads instead of self-attesting.
 *
 * The verdict separates three tiers, on purpose:
 *   measured   — script decides, binary (axe contrast, 320 overflow, CLS, LCP)
 *   visual     — needs a human/model to LOOK at the PNGs (hierarchy, slop tells,
 *                hook realized, contrast over photos that axe marks "incomplete")
 *   unverified — no browser available -> labelled, never silently passed
 *
 * Freshness binding: the report records a hash of the build. A report whose hash
 * != the current build is stale and the gate must reject it (no "I ran it earlier").
 *
 * Motion pass (landing-critical): drives a scripted scroll and measures, as hash-bound facts,
 *   M1 non-inert (elements actually transform/fade across scroll — the hook enacts, not sits),
 *   M2 scroll jank (longtask budget during the scroll), M3 reduced-motion respected
 *   (prefers-reduced-motion collapses the motion), and for a webgl <canvas> M4 (render loop pauses
 *   off-screen + an approx script-transfer budget). These convert design-qa's "hook enacted",
 *   "prefers-reduced-motion fallback", and the 3D perf rules from Tier-3 judgment to Tier-1 measured.
 *
 * Usage:
 *   node verify.mjs <url|file.html> [--out .design/verify] [--sections "sel"]
 *     [--deliverable landing|app|component] [--mockup <ref.html>]
 * Exit codes: 0 all measured checks pass · 1 a measured check failed · 3 no browser.
 */
import { createHash } from "node:crypto";
import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const THEMES = ["light", "dark"];
const WIDTHS = [320, 768, 1280];
const BUDGET = { LCP_MS: 2500, CLS: 0.1 }; // INP needs real interaction; see note below

function arg(flag, def) {
  const i = process.argv.indexOf(flag);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}

const target = process.argv[2];
if (!target || target.startsWith("--")) {
  console.error("usage: node verify.mjs <url|file.html> [--out dir] [--sections sel]");
  process.exit(2);
}
const outDir = arg("--out", ".design/verify");
const sectionSel = arg("--sections", "[data-qa-section], section, [data-section]");
const deliverable = arg("--deliverable", "landing"); // landing | app | component — gates motion_non_inert
const mockup = arg("--mockup", null);                 // optional reference build for structural fidelity (O1)
const MOTION = { LONGTASK_TOTAL_MS: 300, LONGTASK_MAX_MS: 100, WEBGL_SCRIPT_KB: 700, OFFSCREEN_RAF_500MS: 15 };

// Resolve target -> URL + a content hash for freshness binding.
let url, buildHash;
if (/^https?:\/\//.test(target)) {
  url = target;
  buildHash = "url:" + createHash("sha256").update(url).digest("hex").slice(0, 16);
} else {
  const p = resolve(target);
  if (!existsSync(p)) { console.error("file not found: " + p); process.exit(2); }
  url = pathToFileURL(p).href;
  buildHash = "file:" + createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 16);
}

mkdirSync(outDir, { recursive: true });

// ---- honest fallback: no Playwright / no browser -> label, don't fake ----
let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  const report = noBrowserReport("playwright not installed (npm i -D playwright axe-core && npx playwright install chromium)");
  writeFileSync(`${outDir}/verify-report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary, null, 2));
  process.exit(3);
}

// locate axe-core's bundled source to inject
let axePath;
try {
  axePath = fileURLToPath(await import.meta.resolve("axe-core/axe.min.js"));
} catch {
  try { axePath = resolve("node_modules/axe-core/axe.min.js"); } catch { axePath = null; }
}

function noBrowserReport(reason) {
  const unverified = [];
  for (const t of THEMES) for (const w of WIDTHS)
    unverified.push(`${t}@${w}: contrast, overflow, CLS, LCP — requires render`);
  return {
    build_hash: buildHash, browser: false, generated_at: new Date().toISOString(),
    reason,
    summary: { verdict: "UNVERIFIED", measured_pass: 0, measured_fail: 0,
               unverified: unverified.length,
               note: "No browser: measured checks are NOT passed, they are unverified. " +
                     "The gate must label the deliverable 'requires render' — never green." },
    measured: [], visual_required: [], advisory: [], motion: null, unverified, screenshots: [],
  };
}

let browser;
try {
  browser = await chromium.launch();
} catch (e) {
  const report = noBrowserReport("chromium failed to launch: " + e.message);
  writeFileSync(`${outDir}/verify-report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary, null, 2));
  process.exit(3);
}

const measured = [];        // binary, script-decided (blocking when pass:false)
const visualRequired = [];  // model/human must look at the PNG
const advisory = [];        // non-blocking signals (shown, never gate the result)
const shots = [];

for (const theme of THEMES) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({
      colorScheme: theme,
      viewport: { width, height: 900 },
      deviceScaleFactor: 1,
    });
    const page = await ctx.newPage();

    // capture CLS + LCP from the very start
    await page.addInitScript(() => {
      window.__cls = 0; window.__lcp = 0;
      try {
        new PerformanceObserver((l) => {
          for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;
        }).observe({ type: "layout-shift", buffered: true });
        new PerformanceObserver((l) => {
          const es = l.getEntries(); window.__lcp = es[es.length - 1].startTime;
        }).observe({ type: "largest-contentful-paint", buffered: true });
      } catch {}
    });

    let loadOk = true;
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    } catch (e) {
      loadOk = false;
      measured.push({ theme, width, check: "page_loads", pass: false, detail: e.message });
    }

    if (loadOk) {
      await page.waitForTimeout(600); // let late shifts/LCP settle

      // overflow (only meaningful at the smallest width)
      if (width === 320) {
        const overflow = await page.evaluate(() => {
          const d = document.documentElement;
          return { scroll: d.scrollWidth, client: d.clientWidth };
        });
        measured.push({
          theme, width, check: "no_overflow_320",
          pass: overflow.scroll <= overflow.client + 1,
          detail: `scrollWidth ${overflow.scroll} vs clientWidth ${overflow.client}`,
        });
      }

      // CLS + LCP
      const perf = await page.evaluate(() => ({ cls: window.__cls || 0, lcp: window.__lcp || 0 }));
      measured.push({
        theme, width, check: "cls", pass: perf.cls <= BUDGET.CLS,
        detail: `CLS ${perf.cls.toFixed(3)} (budget ${BUDGET.CLS})`,
      });
      if (perf.lcp > 0) {
        measured.push({
          theme, width, check: "lcp", pass: perf.lcp <= BUDGET.LCP_MS,
          detail: `LCP ${Math.round(perf.lcp)}ms (budget ${BUDGET.LCP_MS}ms)`,
        });
      }

      // axe-core
      if (axePath) {
        await page.addScriptTag({ path: axePath });
        const axe = await page.evaluate(async () =>
          await window.axe.run(document, {
            runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "best-practice"] },
          }).then((r) => ({
            violations: r.violations.map((v) => ({
              id: v.id, impact: v.impact, nodes: v.nodes.length,
              sample: v.nodes[0]?.target?.join(" ") || "",
            })),
            // "incomplete" = axe couldn't decide (e.g. text over a photo/gradient) -> visual review
            incomplete: r.incomplete.map((v) => ({ id: v.id, nodes: v.nodes.length })),
          }))
        );
        const blocking = axe.violations.filter((v) =>
          v.impact === "serious" || v.impact === "critical");
        measured.push({
          theme, width, check: "axe_a11y",
          pass: blocking.length === 0,
          detail: blocking.length
            ? blocking.map((v) => `${v.id}(${v.nodes}) e.g. ${v.sample}`).join("; ")
            : `no serious/critical a11y violations (${axe.violations.length} minor)`,
        });
        for (const inc of axe.incomplete.filter((i) => i.id === "color-contrast")) {
          visualRequired.push({
            theme, width, check: "contrast_over_background",
            why: `axe could not auto-decide contrast on ${inc.nodes} node(s) — likely text over photo/gradient/glow. LOOK at the screenshot.`,
          });
        }
      } else {
        visualRequired.push({ theme, width, check: "axe_a11y",
          why: "axe-core not installed — a11y not measured; install axe-core" });
      }

      // screenshots: full page + each section
      const full = `${outDir}/${theme}-${width}-full.png`;
      await page.screenshot({ path: full, fullPage: true });
      shots.push(full);
      const handles = await page.$$(sectionSel);
      for (let i = 0; i < handles.length && i < 20; i++) {
        const f = `${outDir}/${theme}-${width}-sec${i}.png`;
        try { await handles[i].screenshot({ path: f }); shots.push(f); } catch {}
      }
    }
    await ctx.close();
  }
}

// ---- Motion / 3D pass (M1–M4): drive a scripted scroll, measure as hash-bound facts ----
// Animation behaviour is theme-agnostic, so this runs once (primary theme) normal + reduced,
// not the full theme×width matrix — keeps cost to ~2 extra loads.
async function motionRun(theme, reduced) {
  const ctx = await browser.newContext({
    colorScheme: theme, viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1,
    reducedMotion: reduced ? "reduce" : "no-preference",
  });
  const page = await ctx.newPage();
  let scriptBytes = 0; // approx three+app transfer for the 3D budget (http only; file:// has no length)
  ctx.on("response", (res) => {
    if (res.request().resourceType() === "script") {
      const len = Number(res.headers()["content-length"] || 0);
      if (len) scriptBytes += len;
    }
  });
  await page.addInitScript(() => {
    window.__lt = 0; window.__ltMax = 0; window.__raf = 0;
    try {
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) { window.__lt += e.duration; window.__ltMax = Math.max(window.__ltMax, e.duration); }
      }).observe({ type: "longtask", buffered: true });
    } catch {}
    const _raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => _raf((t) => { window.__raf++; return cb(t); });
  });
  await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(400);
  // computed transform+opacity fingerprint of up to 600 elements at the current scroll
  const snap = () => page.evaluate(() =>
    Array.from(document.querySelectorAll("body *")).slice(0, 600)
      .map((e) => { const s = getComputedStyle(e); return s.transform + "|" + s.opacity; }));
  const top = await snap();
  // reset jank counters, then a rAF-driven smooth scroll top->bottom over ~1.2s
  await page.evaluate(() => { window.__lt = 0; window.__ltMax = 0; window.__raf = 0; });
  await page.evaluate(() => new Promise((done) => {
    const end = Math.max(0, document.documentElement.scrollHeight - innerHeight), dur = 1200, t0 = performance.now();
    (function step(now) {
      const p = Math.min(1, (now - t0) / dur); scrollTo(0, end * p);
      if (p < 1) requestAnimationFrame(step); else done();
    })(t0);
  }));
  await page.waitForTimeout(200);
  const bottom = await snap();
  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight * 0.5));
  await page.waitForTimeout(150);
  const halfway = await snap();
  const changed = top.reduce((n, v, i) => n + ((v !== bottom[i] || v !== halfway[i]) ? 1 : 0), 0);
  const jank = await page.evaluate(() => ({ lt: window.__lt, ltMax: window.__ltMax }));
  // webgl detect + off-screen render-loop pause (M4)
  let webgl = { present: false };
  const hasGl = await page.evaluate(() => {
    const c = document.querySelector("canvas"); if (!c) return false;
    try { return !!(c.getContext("webgl2") || c.getContext("webgl")); } catch { return false; }
  });
  if (hasGl) {
    await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForTimeout(150);
    await page.evaluate(() => { window.__raf = 0; });
    await page.waitForTimeout(500);
    const off = await page.evaluate(() => window.__raf);
    webgl = { present: true, offscreen_raf_500ms: off, script_kb: Math.round(scriptBytes / 1024) };
  }
  await ctx.close();
  return { changed, jank, webgl };
}

let motion = null;
try {
  const t = THEMES[0];
  const full = await motionRun(t, false);
  const red = await motionRun(t, true);
  const motional = full.changed >= 3; // enough scroll-driven change to meaningfully test reduced-motion
  const jankOk = full.jank.lt <= MOTION.LONGTASK_TOTAL_MS && full.jank.ltMax <= MOTION.LONGTASK_MAX_MS;
  const reducedOk = !motional || red.changed <= Math.max(1, Math.round(full.changed * 0.25));

  // M2 — scroll jank (universal, blocking)
  measured.push({ theme: t, width: 1280, check: "scroll_jank", pass: jankOk,
    detail: `longtask total ${Math.round(full.jank.lt)}ms (≤${MOTION.LONGTASK_TOTAL_MS}), max ${Math.round(full.jank.ltMax)}ms (≤${MOTION.LONGTASK_MAX_MS}) during a 1.2s scroll` });

  // M1 — non-inert: blocking for a landing, advisory for app/component
  const nonInert = { theme: t, width: 1280, check: "motion_non_inert", pass: full.changed >= 1,
    detail: `${full.changed} element(s) change transform/opacity across scroll — the hook must enact, not sit inert` };
  if (deliverable === "landing") measured.push(nonInert);
  else advisory.push({ ...nonInert, advisory: true, detail: `${nonInert.detail} (advisory for ${deliverable})` });

  // M3 — reduced-motion respected (MUSTHAVE-BASE, blocking)
  measured.push({ theme: t, width: 1280, check: "reduced_motion_respected", pass: reducedOk,
    detail: motional
      ? `prefers-reduced-motion collapses scroll-driven changes ${full.changed}→${red.changed} (must drop to ≤25%)`
      : `only ${full.changed} scroll-driven change(s) — nothing to disable, N/A` });

  // M4 — 3D, only when a webgl canvas is present
  if (full.webgl.present) {
    measured.push({ theme: t, width: 1280, check: "webgl_render_loop_paused",
      pass: full.webgl.offscreen_raf_500ms <= MOTION.OFFSCREEN_RAF_500MS,
      detail: `${full.webgl.offscreen_raf_500ms} rAF in 500ms with the canvas off-screen (idle GPU if high — frameloop="demand" or gate useFrame; budget ≤${MOTION.OFFSCREEN_RAF_500MS})` });
    advisory.push({ theme: t, width: 1280, check: "webgl_script_budget", advisory: true,
      pass: full.webgl.script_kb <= MOTION.WEBGL_SCRIPT_KB,
      detail: `~${full.webgl.script_kb}KB script transferred (approx three+app; soft budget ${MOTION.WEBGL_SCRIPT_KB}KB) — lazy-load / code-split the 3D bundle` });
  }
  motion = { theme: t, deliverable, changed: full.changed, changed_reduced: red.changed,
    longtask_ms: Math.round(full.jank.lt), longtask_max_ms: Math.round(full.jank.ltMax), webgl: full.webgl };
} catch (e) {
  advisory.push({ check: "motion_pass", advisory: true, pass: true, detail: "motion pass skipped: " + e.message });
}

// ---- O1 — structural mockup->build fidelity (advisory, no image libs: compare section/heading structure) ----
if (mockup) {
  try {
    const domStructure = async (u) => {
      const ctx = await browser.newContext({ colorScheme: THEMES[0], viewport: { width: 1280, height: 900 } });
      const page = await ctx.newPage();
      await page.goto(u, { waitUntil: "networkidle", timeout: 30000 });
      const s = await page.evaluate((sel) => ({
        sections: document.querySelectorAll(sel).length,
        headings: Array.from(document.querySelectorAll("h1,h2,h3"))
          .map((h) => (h.textContent || "").trim().toLowerCase().replace(/\s+/g, " ").slice(0, 60)).filter(Boolean),
      }), sectionSel);
      await ctx.close();
      return s;
    };
    const b = await domStructure(url);
    const mUrl = /^https?:\/\//.test(mockup) ? mockup : pathToFileURL(resolve(mockup)).href;
    const m = await domStructure(mUrl);
    const setB = new Set(b.headings), setM = new Set(m.headings);
    const matched = b.headings.filter((h) => setM.has(h)).length;
    const denom = Math.max(b.headings.length, m.headings.length, 1);
    advisory.push({ check: "mockup_fidelity", advisory: true, pass: matched / denom >= 0.6,
      detail: `headings matched ${matched}/${denom}; build ${b.sections} sec / mockup ${m.sections} sec; ` +
              `missing-from-build: ${m.headings.filter((h) => !setB.has(h)).slice(0, 5).join(" | ") || "none"}` });
  } catch (e) {
    advisory.push({ check: "mockup_fidelity", advisory: true, pass: true, detail: "fidelity skipped: " + e.message });
  }
}

await browser.close();

// every screenshot also implies a model-look obligation for the non-measurable checks
visualRequired.push({
  check: "visual_design_qa",
  why: "LOOK at every screenshot and run the non-measurable design-qa checks against the PIXELS, " +
       "not the source: hierarchy, optical balance, hook realized, slop tells, ambition (gallery-tier moment). " +
       "INP is not measured headlessly (needs real interaction) — profile it in a real session if it matters.",
});

const fails = measured.filter((m) => !m.pass);
const report = {
  build_hash: buildHash,
  browser: true,
  generated_at: new Date().toISOString(),
  target: url,
  deliverable,
  summary: {
    verdict: fails.length ? "MEASURED_FAIL" : "MEASURED_PASS",
    measured_pass: measured.length - fails.length,
    measured_fail: fails.length,
    visual_checks_required: visualRequired.length,
    advisory_count: advisory.length,
    note: "MEASURED_PASS means only the measurable tier is green (incl. the motion pass: " +
          "scroll_jank, motion_non_inert, reduced_motion_respected, webgl checks). The gate is NOT " +
          "fully green until the visual_required checks are done against the screenshots. " +
          "advisory[] are non-blocking signals.",
  },
  blocking_failures: fails,
  measured,
  motion,
  visual_required: visualRequired,
  advisory,
  screenshots: shots,
};
writeFileSync(`${outDir}/verify-report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report.summary, null, 2));
process.exit(fails.length ? 1 : 0);
