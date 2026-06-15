# Anti-Slop — what NOT to do

Read this first, every time. Generic "AI slop" is the **default output** of a language model — it is the median of a million training examples, and the median is by definition boring. Avoiding it is not automatic; it takes deliberate refusal of specific defaults.

## Two tiers of prohibition

- **TIER 1 — hard bans (MUSTHAVE-BASE).** Never, in any output. These are the slop tells with the highest recognition value. Building one is a defect, not a choice.
- **TIER 2 — banned-by-default (MUSTHAVE-DEFAULT).** The *technique* isn't evil; the *thoughtless default* is. Allowed only when the stated concept earns it and the survey/owner approved it — exactly like Inter-as-body. If you reach for one of these on autopilot, that reflex IS the slop.

The principle under both: a pattern is rarely bad alone — it's bad as an unconsidered default that 60,000 other AI sites also reached for.

**Stable rules here, dated instances in `tells-current.md`.** This file holds the durable
principles and the *generalized* tells (e.g. "the pill/capsule carrier IS the tell"). The
**time-bound specifics** — which exact fonts, gradients, components, and copy clichés are tells
*right now* — live in `principles/tells-current.md`, which carries provenance and refreshes on a
30-day cycle (`tools/preflight.mjs` proposes the refresh when stale; see `reference-scout.md` →
"Refreshing the tells"). Read both: the generalized rules below are always binding; the dated
catalog is the current instance list. The examples named below are illustrative of the rules and
are mirrored, with dates and sources, in the catalog.

## TIER 1 — hard bans (never)

**Fonts.** Never default to Inter, Roboto, Arial, or raw system fonts for the display/headline voice. Never the "Space Grotesk / Geist" + serif-italic-accent-word combo (a 2026 tell). Never the Playfair-Display + Inter "tasteful" pairing as a default. No wobbly/blobby illegible display type; no inflated/"puffy" 3D type effects. (Inter et al. may be a *body* font when genuinely right — never the voice.)

**Color.** No purple/indigo/violet as default accent. No purple-gradient-on-white/dark. No **aurora-gradient background** (the breathing 6s purple-pink-cyan / orange-amber wash) — this is the single loudest "this is AI" signal of 2026. No AI-default golden/honey-hued wash. No lavender→midnight-blue-on-cream "premium minimalism" default. **"Wow" is never "more colors": a flawless neutral scale + exactly ONE accent.**

**Gradient text.** No gradient-filled H1 / hero headline. It reads as templated instantly.

**Glow & shimmer.** No radial glow / light-bloom sitting behind the hero "for atmosphere" — dark+glow=premium is a learned reflex applied everywhere, and the glow carries no meaning (not interaction, status, or hierarchy); it just competes with content. No "glow on everything", no shimmer/sparkle decoration used as content, no gradient-filled buttons as a default.

**Layout templates.** No centered single-column stacks. No canonical AI hero `[badge-pill] [H1] [subhead] [two buttons] [phone/UI mockup]`. No 3- or 6-column "features grid" of `icon + title + two lines`. No bento grid *as the only structuring idea*. No identical-looking sections in a row. No badge-pill floating above the H1.

**The capsule/pill tell (generalised).** The most recognisable AI component is the **pill/capsule** carrier: a small rounded capsule with a thin border, often a dot or pulsing circle and an ALL-CAPS mono label ("NOW PLAYING", "— LIVE"). The carrier *is* the tell — banning only the word "badge" missed it; it's the **pill shape used to float status/meta**. Don't build it. Show status as real typography in the layout (a line with a rule above it, a number in a corner, a labelled value), or as a normal sentence. The same goes for: all-caps mono section labels, numbered 1-2-3 step strips, and stat-number banners used as filler.

**Components.** No browser-default `<select>`/checkbox/radio (reads unfinished). No **colored left-border on cards** (the 3-4px purple/blue/gradient stripe — "as reliable a tell as the em-dash is for AI text"). No row of identical icon-feature cards. No **prompt-input box as the hero CTA** ("What do you want to build?") with a glowing animated border. No floating pulsing chat-bubble bottom-right. No 3-tier pricing with a sparkle on the middle "Pro". No Discord-badge + GitHub-stars-counter footer combo. No raw shadcn defaults shipped as-is (the library is built for AI copy-paste — its untouched tokens light up as slop).

**Effects.** No claymorphism default (puffy rounded corners + soft gradients + thick inner/outer shadows). No glassmorphism as a default surface (glossy "sandblasted" glass cards). No corporate-soft-UI default (the `box-shadow: 0 8px 24px` + 12-16px radius + floating card stack — already being phased out, reads dated).

**Imagery.** No generic stock people. No Corporate-Memphis / humaaans / Alegria illustration (bendy limbs, tiny heads, blank faces, blue/purple/green skin) or its 3D iteration. No gradient-blob / "blobitecture" amoeba shapes as background. No abstract-gradient-swirl logo (the mark ~62,000 AI startups independently arrived at). No token-streamed IDE/code mockup with a blinking caret as the hero proof. No "stock photo + gradient overlay". No AI caricatures. No Y3K chrome/iridescent as a default flex.

**Iconography.** No emoji, ever. No sparkle ✨ / checkmark glyphs / emoji used as iconography. No sidebar with emoji icons. (Line icons like Lucide are fine — they're a deliberate icon set, not emoji.)

**Copy (text is part of the design).** No stock phrases: empower, unlock, next level, seamless, elevate, supercharge, revolutionize, game-changing, "Powered by AI", "The future of X", "Build what's next". No `<noun> for <persona>` hero formula ("Frontier intelligence for builders"). No future-gesturing subhead that says nothing. No em-dash-as-AI-tell or other AI-text markers in rendered copy.

**Filler.** No lorem ipsum. No fake avatars (UI Faces, Pravatar). No fake company logos. No "Trusted by" row of invented logos (especially with OpenAI's mark slipped in). No generic dashboard mockups as filler.

**The aggregate syndrome.** When several of the above co-occur — aurora background + gradient H1 + prompt-box hero + sparkles + glass cards + "Trusted by" + pricing-sparkle — it stops being individual tells and becomes the "AI-startup recipe". Catch it as a whole: if a page is assembling this kit, the problem is the kit, not the parts.

## TIER 2 — banned-by-default, allowed only with stated intent

These are NOT tells when used deliberately and made to fit the concept; they ARE slop as an unconsidered reflex. Don't reach for them on autopilot; if the concept calls for one, say so and do it properly.

- **Dark mode** — fine with meaningful hierarchy; slop only when paired reflexively with glow as "premium".
- **Bento grid** — a legitimate modular layout the industry settled on (Apple/Google/Spotify use it); slop only as the *single* idea.
- **Glassmorphism, mature** — fine when it models real material honesty (how glass catches light, relates to its background); slop as a glossy default surface.
- **Gradients** — subtle/purposeful gradients are fine; the slop is the unconsidered gradient-as-decoration.
- **3D / WebGL** — fine when motion helps the user and the perf budget allows; slop when it's flex that tanks mobile.
- **Minimalism** — fine as a real philosophy (every element earns its place); slop when it's a cover for having no visual ideas (this is `ambition.md`'s "timid-but-correct is also slop").

## The root cause and the cure

Slop is not a settings bug — it is what the model reverts to without strong context. The cure, throughout this skill:

1. **Narrate the intent in words before writing code.** Forcing an explicit design narrative pulls Claude out of the median.
2. **Commit to a bold, specific aesthetic direction.** Intentionality, not intensity — refined minimalism and loud maximalism both work; timid middle-ground does not.
3. **Apply technique stacks, not single choices.** A boring headline is boring because *no* technique was applied to it, not because the font is wrong.
4. **Intensity by hierarchy.** Not everything should shout. A hero is rich; an ordinary section is calm. Uniform intensity reads as noise.

## The tell test

Before shipping any screen, ask: *what is the one thing someone will remember about this?* If the honest answer is "nothing" — it is slop. Go back and give it a point of view.

**Timid-but-correct is also slop.** A page can pass every prohibition above and still be the median: tasteful, safe, forgettable. Clearing the floor is not clearing the bar. The companion to this file is `ambition.md` — the floor against *forgettable* — and it is equally binding. The real test is not only "is it free of tells" but "would it place in a gallery". A clean correct landing that no one would remember failed, even with zero slop in it.

