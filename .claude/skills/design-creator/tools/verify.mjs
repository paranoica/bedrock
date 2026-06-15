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
 * Usage:
 *   node verify.mjs <url|file.html> [--out .design/verify] [--sections "section,[data-qa-section]"]
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
    measured: [], visual_required: [], unverified, screenshots: [],
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

const measured = [];        // binary, script-decided
const visualRequired = [];  // model/human must look at the PNG
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
  summary: {
    verdict: fails.length ? "MEASURED_FAIL" : "MEASURED_PASS",
    measured_pass: measured.length - fails.length,
    measured_fail: fails.length,
    visual_checks_required: visualRequired.length,
    note: "MEASURED_PASS means only the measurable tier is green. The gate is NOT fully " +
          "green until the visual_required checks are done against the screenshots.",
  },
  blocking_failures: fails,
  measured,
  visual_required: visualRequired,
  screenshots: shots,
};
writeFileSync(`${outDir}/verify-report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report.summary, null, 2));
process.exit(fails.length ? 1 : 0);
