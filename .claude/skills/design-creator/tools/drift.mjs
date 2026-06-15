#!/usr/bin/env node
/**
 * drift.mjs — keep the large principles/ surface in sync with the core.
 *
 * Two real failure modes at 35+ principle files:
 *   (1) ROUTING DRIFT — a principle file exists but isn't named in SKILL.md's file map, or
 *       isn't referenced anywhere in index.json (the ACTUAL router — a principle absent from it
 *       is never lazy-loaded), or the map names a file that's gone.
 *   (2) CORE DRIFT — `anti-slop.md` (the floor) changes, but a principle that should
 *       have been re-reconciled against it never was. We can't detect "should" by
 *       mtime (unreliable across checkout/zip), so we anchor on a content hash: each
 *       principle records the anti-slop hash it was last reconciled against; when
 *       anti-slop's hash moves, every principle still pinned to the old hash is flagged
 *       for re-review. This is advisory, not auto-edit — it produces a reviewable list.
 *
 * Commands:
 *   check        # report routing drift + principles pinned to a stale anti-slop hash (exit 1 if any)
 *   seed         # (re)write the manifest: pin every principle to the CURRENT anti-slop hash
 *   reconcile <file...>   # after re-reviewing named principle(s), re-pin them to current hash
 *
 * Manifest: principles/.reviewed.json  (committed). stdlib/node only.
 */
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, resolve, basename } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const PRIN = resolve(ROOT, "principles");
const ANTI = resolve(PRIN, "anti-slop.md");
const SKILL = resolve(ROOT, "SKILL.md");
const INDEX = resolve(ROOT, "index.json");
const MANIFEST = resolve(PRIN, ".reviewed.json");

const h = (p) => createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 16);

function principleFiles() {
  return readdirSync(PRIN).filter((f) => f.endsWith(".md")).sort();
}

function loadManifest() {
  if (!existsSync(MANIFEST)) return { anti_slop_hash: null, pinned: {} };
  try { return JSON.parse(readFileSync(MANIFEST, "utf8")); }
  catch { return { anti_slop_hash: null, pinned: {} }; }
}

function routingDrift() {
  const skill = readFileSync(SKILL, "utf8");
  const index = readFileSync(INDEX, "utf8");
  const files = principleFiles();
  // a principle is "routed" if SKILL.md names it (bare filename match in the file map)
  const unrouted = files.filter((f) => !skill.includes(f) && f !== ".reviewed.json");
  // ...and it must also be referenced in index.json — the actual router that drives lazy loading
  // (a principle listed only in SKILL.md prose is documented but never loaded for any task).
  const unroutedInIndex = files.filter((f) => !index.includes(f) && f !== ".reviewed.json");
  // and flag any principles/<x>.md referenced in SKILL that no longer exists
  const referenced = [...skill.matchAll(/`?([a-z0-9-]+\.md)`?/g)].map((m) => m[1]);
  const known = new Set(files);
  const dangling = [...new Set(referenced)].filter(
    (r) => skill.includes(`principles/`) && r.endsWith(".md") &&
           !known.has(r) && new RegExp(`principles/${r}\\b`).test(skill)
  );
  return { unrouted, unroutedInIndex, dangling };
}

function check() {
  const cur = h(ANTI);
  const man = loadManifest();
  const files = principleFiles().filter((f) => f !== "anti-slop.md");
  const stale = files.filter((f) => (man.pinned[f] || null) !== cur);
  const { unrouted, unroutedInIndex, dangling } = routingDrift();
  const out = {
    anti_slop_hash: cur,
    manifest_hash: man.anti_slop_hash,
    routing: { unrouted, unrouted_in_index: unroutedInIndex, dangling },
    stale_against_anti_slop: stale,
    clean: !unrouted.length && !unroutedInIndex.length && !dangling.length && !stale.length,
    note: "stale_against_anti_slop = principles last reconciled against an older anti-slop.md; " +
          "re-review them and run `reconcile <file>`. unrouted = principle not in SKILL.md file map; " +
          "unrouted_in_index = principle absent from index.json (the router) so it is never lazy-loaded " +
          "— add it to a task_route or contextual_load. Advisory only — nothing is auto-edited.",
  };
  console.log(JSON.stringify(out, null, 2));
  process.exit(out.clean ? 0 : 1);
}

function seed() {
  const cur = h(ANTI);
  const pinned = {};
  for (const f of principleFiles()) if (f !== "anti-slop.md") pinned[f] = cur;
  writeFileSync(MANIFEST, JSON.stringify({ anti_slop_hash: cur, pinned }, null, 2) + "\n");
  console.log(JSON.stringify({ seeded: Object.keys(pinned).length, anti_slop_hash: cur }, null, 2));
}

function reconcile(args) {
  if (!args.length) { console.error("usage: drift.mjs reconcile <file.md> [...]"); process.exit(2); }
  const cur = h(ANTI);
  const man = loadManifest();
  man.anti_slop_hash = cur;
  const done = [];
  for (const a of args) {
    const f = basename(a);
    if (existsSync(resolve(PRIN, f))) { man.pinned[f] = cur; done.push(f); }
  }
  writeFileSync(MANIFEST, JSON.stringify(man, null, 2) + "\n");
  console.log(JSON.stringify({ reconciled: done, anti_slop_hash: cur }, null, 2));
}

const [cmd, ...rest] = process.argv.slice(2);
if (cmd === "check") check();
else if (cmd === "seed") seed();
else if (cmd === "reconcile") reconcile(rest);
else { console.error("usage: drift.mjs check | seed | reconcile <file...>"); process.exit(2); }
