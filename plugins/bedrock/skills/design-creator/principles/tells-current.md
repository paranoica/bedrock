# Current AI tells — the dated catalog (refreshes on a cycle)

<!--meta
last_refreshed: 2026-06-11
refresh_interval_days: 30
source_pass: reference-scout
-->

This is the **volatile** half of anti-slop. `anti-slop.md` holds the *stable principles* (the
two-tier model, the root cause, the tell test, the generalized rules like "the pill/capsule
carrier IS the tell"). This file holds the **time-bound instances** — the specific fonts,
gradients, components, and copy clichés that are tells *right now* and that age out. Splitting
them means the durable reasoning never churns and only this catalog refreshes.

**How it refreshes.** Every `refresh_interval_days` (30), `tools/preflight.mjs` flags this file
as stale and the engine *proposes* a refresh (it never auto-edits). The refresh is a
`reference-scout` web pass (see `reference-scout.md` → "Refreshing the tells") that produces a
**reviewable diff**: new tells to add, current tells to retire. Each change carries provenance so
both additions and retirements are auditable. The owner approves the diff; nothing changes silently.

**Provenance fields** per tell: `first_seen` (when it became a recognizable tell), `source`
(where it was observed/reported), `status` (`active` | `watch` | `retiring`). A tell is **retired**
(moved to the graveyard below) with the same rigor it's added — a retired tell that's no longer a
reliable signal but stays in the list causes false positives on legitimate design.

---

## Active tells (TIER 1 instances — currently high recognition value)

- **Aurora-gradient background** — the breathing 6s purple-pink-cyan / orange-amber wash.
  `first_seen: 2024` · `source: ubiquitous AI-startup landing pages` · `status: active`. Still the
  single loudest "this is AI" signal.
- **"Space Grotesk / Geist" + serif-italic-accent-word** display combo.
  `first_seen: 2025` · `source: AI dev-tool & startup sites` · `status: active`.
- **Playfair-Display + Inter "tasteful" pairing** as a default.
  `first_seen: 2024` · `source: template marketplaces` · `status: active`.
- **Purple/indigo/violet default accent**, purple-gradient-on-white/dark.
  `first_seen: 2023` · `source: generic LLM output` · `status: active`.
- **Gradient-filled H1 / hero headline.** `first_seen: 2023` · `source: AI page builders` · `status: active`.
- **Radial glow / light-bloom behind the hero** ("dark + glow = premium").
  `first_seen: 2023` · `source: SaaS landing trend` · `status: active`.
- **Colored left-border stripe on cards** (3–4px purple/blue/gradient).
  `first_seen: 2024` · `source: shadcn-derived UIs` · `status: active`.
- **Prompt-input box as the hero CTA** ("What do you want to build?") with a glowing animated border.
  `first_seen: 2024` · `source: AI product homepages` · `status: active`.
- **Abstract-gradient-swirl logo** (the mark ~62,000 AI startups arrived at).
  `first_seen: 2023` · `source: startup branding` · `status: active`.
- **Token-streamed IDE/code mockup** with a blinking caret as hero proof.
  `first_seen: 2024` · `source: AI coding-tool sites` · `status: active`.
- **Raw shadcn defaults shipped as-is** (untouched tokens light up as slop).
  `first_seen: 2024` · `source: AI copy-paste UIs` · `status: active`.
- **Floating pulsing chat-bubble bottom-right**; **3-tier pricing with a sparkle on "Pro"**;
  **Discord-badge + GitHub-stars footer combo**.
  `first_seen: 2023–2024` · `source: SaaS template kits` · `status: active`.
- **Corporate-Memphis / humaaans / Alegria illustration** (and its 3D iteration).
  `first_seen: 2020` · `source: big-tech marketing` · `status: active` (long-lived but still a tell).
- **Sparkle ✨ as AI-iconography**; emoji as iconography.
  `first_seen: 2023` · `source: "AI feature" badges` · `status: active`.
- **Copy clichés** — empower, unlock, next level, seamless, elevate, supercharge, revolutionize,
  game-changing, "Powered by AI", "The future of X", "Build what's next"; the `<noun> for <persona>`
  hero formula. `first_seen: 2023` · `source: LLM marketing copy` · `status: active`.

## Watch (emerging — not yet a hard ban, flag if stacking)

- **Corporate-soft-UI** (`box-shadow: 0 8px 24px` + 12–16px radius + floating card stack).
  `first_seen: 2022` · `source: dribbble-era SaaS` · `status: retiring` — already dated; treat as a
  watch item, not a fresh tell. Retire next cycle if it stops appearing in new AI output.
- **Y3K chrome / iridescent** as a default flex. `first_seen: 2025` · `source: trend-chasing rebrands` · `status: watch`.
- **Glass / soft-futurism as a default surface** (when not modelling real material).
  `first_seen: 2024` · `source: Apple-adjacent imitation` · `status: watch`.

## Graveyard (retired tells — no longer reliable signals; do NOT flag)

*(empty at first split — populate as the scout retires tells, with the date + reason, so we can
audit why a once-tell stopped being one.)*

---

**Note for the engine:** treat `active` as TIER-1 hard bans (per `anti-slop.md`), `watch` as
TIER-2 "flag if stacking with others", `retiring`/graveyard as **not** a tell (flagging it risks a
false positive on legitimate, now-acceptable design). The generalized rules in `anti-slop.md`
remain binding regardless of this catalog's freshness.
