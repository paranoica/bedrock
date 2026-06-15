#!/usr/bin/env node
/**
 * preflight.mjs — probe the QA toolchain ONCE at session start so the engine
 * announces the QA mode UP FRONT instead of discovering a missing browser mid-loop.
 * It does not render (verify.mjs does). It answers: is playwright importable, is a
 * browser installed, is axe-core resolvable — and derives qa_mode.
 *   "measured"        — verify.mjs can render+axe+CWV → gate runs with teeth
 *   "requires-render" — no browser → gate labels measured checks "requires render",
 *                       never green; the critic + visual judgement still run.
 * Usage: node tools/preflight.mjs   ·   Output: JSON on stdout.   ·   Exit: always 0.
 */
const out = {
  node: process.version, playwright_importable: false, browser_installed: false,
  axe_resolvable: false, qa_mode: "requires-render", install_hints: "", note: "",
};
try {
  const pw = await import("playwright");
  out.playwright_importable = true;
  try {
    const p = pw.chromium.executablePath();
    const { existsSync } = await import("node:fs");
    out.browser_installed = !!p && existsSync(p);
  } catch { out.browser_installed = false; }
} catch { out.playwright_importable = false; }
try { await import.meta.resolve("axe-core/axe.min.js"); out.axe_resolvable = true; }
catch {
  try {
    const { existsSync } = await import("node:fs");
    const { resolve } = await import("node:path");
    out.axe_resolvable = existsSync(resolve("node_modules/axe-core/axe.min.js"));
  } catch { out.axe_resolvable = false; }
}
const hints = [];
if (!out.playwright_importable) hints.push("playwright: (cd tools && npm i) then `npx playwright install chromium`");
else if (!out.browser_installed) hints.push("browser: npx playwright install chromium");
if (!out.axe_resolvable) hints.push("axe-core: (cd tools && npm i)");
out.qa_mode = (out.playwright_importable && out.browser_installed && out.axe_resolvable) ? "measured" : "requires-render";
out.install_hints = hints.length ? hints.join("; ") : "none — verify.mjs can render";
out.note = out.qa_mode === "measured"
  ? "Gate runs with teeth: verify.mjs renders {light,dark}×{320,768,1280}, axe + CWV, hash-bound report."
  : "Gate in requires-render mode: measured checks LABELLED 'requires render', NEVER auto-green (verify.mjs emits UNVERIFIED, exit 3). Critic + visual judgement still run.";

// --- Critic tier: the independent-critic step is mandatory; its mechanism tiers by host.
// We can't probe Task-subagent availability from here (it's a host property), so we surface
// the requirement up front: the gate MUST state which tier ran and never show green on a
// skipped critic. Tier A = fresh-context Task subagent (preferred); B = registered
// design-critic agent; C = single-context self-critique (labelled lower-assurance).
out.critic = {
  required: true,
  tier_set_at: "runtime",
  note: "Spawn the critic (tools/critic.md) on EVERY result. Prefer Tier A (Task subagent). " +
        "If no subagent host, fall to Tier C self-critique as a FORCED re-derivation against " +
        "critic.md + the exemplar, and label it lower-assurance in what the owner sees. " +
        "State the critic tier in the result banner; never show the QA gate green on a skipped critic.",
};

// --- Tells freshness (principles/tells-current.md) — propose a refresh when stale, never auto-edit.
out.tells = { status: "unknown", note: "" };
try {
  const { readFileSync, existsSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const { dirname, resolve } = await import("node:path");
  const here = dirname(fileURLToPath(import.meta.url));
  const tellsPath = resolve(here, "../principles/tells-current.md");
  if (existsSync(tellsPath)) {
    const txt = readFileSync(tellsPath, "utf8");
    const lr = (txt.match(/last_refreshed:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/) || [])[1];
    const iv = parseInt((txt.match(/refresh_interval_days:\s*(\d+)/) || [])[1] || "30", 10);
    if (lr) {
      const days = Math.floor((Date.now() - Date.parse(lr)) / 86400000);
      const stale = days >= iv;
      out.tells = {
        status: stale ? "stale" : "fresh", last_refreshed: lr, interval_days: iv, age_days: days,
        note: stale
          ? `tells-current.md is ${days}d old (>= ${iv}d). PROPOSE a refresh: run the reference-scout 'Refreshing the tells' pass, present a reviewable add/retire diff with provenance, get owner approval. Do NOT auto-edit.`
          : `tells-current.md fresh (${days}/${iv}d).`,
      };
    } else out.tells = { status: "no-meta", note: "tells-current.md present but missing last_refreshed meta." };
  } else out.tells = { status: "absent", note: "principles/tells-current.md not found; using anti-slop.md only." };
} catch (e) { out.tells = { status: "error", note: String(e && e.message || e) }; }

process.stdout.write(JSON.stringify(out, null, 2) + "\n");
