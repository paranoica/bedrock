/**
 * deps.mjs — where the QA tools find Playwright, axe-core and a browser.
 *
 * Inside a plugin the skill folder is replaced on every update, so `npm i` next to the
 * skill does not last. Libraries are looked up next to the skill first, then in a shared
 * folder bedrock installs once (DESIGN_TOOLS_DIR, default ~/.cache/bedrock/design-tools).
 * A browser: Playwright's own Chromium first, then an installed Chrome or Chromium.
 */
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const SHARED = process.env.DESIGN_TOOLS_DIR || join(homedir(), ".cache", "bedrock", "design-tools");
const shared = createRequire(join(SHARED, "package.json"));

const SYSTEM_BROWSERS = [
  "/opt/google/chrome/chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
];

export async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    // Loaded by path it is the CommonJS build: its exports sit under `default`.
    const mod = await import(pathToFileURL(shared.resolve("playwright")).href);
    return mod.chromium ? mod : mod.default;
  }
}

export function axeFile() {
  try {
    return fileURLToPath(import.meta.resolve("axe-core/axe.min.js"));
  } catch {
    try { return shared.resolve("axe-core/axe.min.js"); } catch { return null; }
  }
}

export function systemBrowser() {
  return SYSTEM_BROWSERS.find((p) => existsSync(p)) || null;
}

export async function launch(chromium) {
  try {
    return await chromium.launch();
  } catch (error) {
    const path = systemBrowser();
    if (!path) throw error;
    return await chromium.launch({ executablePath: path });
  }
}
