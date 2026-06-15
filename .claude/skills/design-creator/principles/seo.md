# SEO / Discoverability

The frontend's share of findability — for classic search and for AI answer engines (GEO). This module covers only what design and frontend actually control: rendering, document head, structured data, semantics, and Core Web Vitals. **Out of scope (hand off to other disciplines): off-site links, brand authority, and editorial content strategy.** The same boundary discipline as "not for non-web deliverables".

Two facts frame everything here: AI answer engines retrieve **chunks, not pages**, and they must be able to parse a clean DOM before they'll cite anything — so structure and machine-readability are now ranking *and* citation factors, not just niceties. And classic CWV stopped being a tiebreaker: a page in the red is filtered down even with good content.

## 1. Rendering — content must exist in the first HTML (MUSTHAVE-BASE)

- Public-facing pages use **SSR / SSG / ISR**, not client-only rendering. Crawlers and AI retrievers often don't execute JS; content that only appears after hydration is invisible to them.
- Everything in `<head>` must be in the **initial HTML**, not injected by a deferred script.
- Avoid hydration mismatches (server HTML must agree with client state) — AI crawlers flag mismatched content as a trust risk.
- This couples with `perf-budget.md` and `frontend-safety.md`.

## 2. Document `<head>` essentials (MUSTHAVE-BASE)

Every page carries, unique per URL:

- `<title>` — the strongest single on-page signal. ~50–60 chars; primary term in the first ~30; brand at the end after a separator.
- `<meta name="description">` — self-contained; AI Overviews often lift it verbatim into the citation snippet, so it's a GEO asset, not just a click driver.
- `<link rel="canonical">` — kills duplicate-URL dilution.
- `<meta name="viewport">`, `lang` on `<html>`, and a sensible `robots` directive.

## 3. Structured data — JSON-LD by page type (MUSTHAVE-BASE for content pages)

- Inject `application/ld+json` in `<head>`, generated **programmatically by page type**: `Organization`, `Product`, `Article`, `FAQPage`, `BreadcrumbList`, `LocalBusiness`.
- The schema **must match the visible DOM** — mismatched schema loses rich results and reads as a trust risk.
- `FAQPage` is the highest-leverage single schema for AI Overviews — they pull Q/A pairs aggressively.

## 4. Open Graph + X Card (MUSTHAVE-DEFAULT)

- Required OG: `og:title`, `og:type`, `og:image`, `og:url`; add `og:description`, `og:image:alt`. Plus `twitter:card` (usually `summary_large_image`).
- OG image 1200×630; a branded template, optionally generated per page.
- A 30-minute task with long-tail ROI — links render as rich cards in Slack/LinkedIn/Discord, and AI reads the metadata.

## 5. Semantics + heading hierarchy (MUSTHAVE-BASE — shared with accessibility)

- Real landmarks, one `<h1>`, a logical H1–H6 hierarchy, buttons vs links used correctly.
- This is the same work as `accessibility.md` semantics — here it's also the "machine experience" layer that makes an LLM crawler able to parse and cite the brand. Do it once, claim both.

## 6. Answer-first + chunk-extractability (structure, not copy)

The engine controls layout and structure even when it doesn't write the words:

- Lead each section with its answer; don't bury it under context.
- Short paragraphs; lists and tables where they fit; explicit Q/A blocks.
- Pages with structured lists, stats, and quotes show markedly higher AI-answer visibility. (Copy itself stays the user's job — but the structure that makes copy extractable is ours.)

## 7. Core Web Vitals as a findability budget (MUSTHAVE-BASE)

Thresholds, measured via `tools/verify.md`, not asserted:

- **LCP < 2.5s**, **INP < 200ms**, **CLS < 0.1**.
- **INP** is the most-failed metric — it's about JS responsiveness across the *whole* session, so heavy animations and scripts hurt it. This is where the perf-budget ax actually bites the Statement techniques (`perf-budget.md`).
- CLS ties directly to the image rules (explicit `width`/`height`/`aspect-ratio`) and to anti-FOUC theming.

## 8. Image SEO

- `alt` on meaningful images (decorative ones hidden from AT); `width`/`height`/`aspect-ratio` to reserve space (CLS); responsive sources; lazy-load below the fold; `priority` on the LCP image. Overlaps `photography.md` and `optimization.md` — extend, don't duplicate.

## 9. Machine-readable artifacts (llms.txt, robots, sitemap)

Generate the files that help machines navigate, as build artifacts:

- **`sitemap.xml`** and a sane **`robots.txt`** — crawl hygiene; block low-value URL patterns, point at the sitemap.
- **`llms.txt`** at the domain root — a curated, markdown-formatted map of the most important content for LLMs. Emerging 2024→2026; not yet read everywhere, so treat as forward-looking enhancement, not a dependency.

## 10. Machine experience = the semantic layer, doubled

"AI-readable" is not a separate workstream — it *is* clean semantics + ARIA + heading hierarchy (section 5) plus structured data (section 3) plus content in the first HTML (section 1). The same work that serves a screen reader serves an LLM crawler. Build it once; it pays both the accessibility and the citation account.

## 11. KPI framing (for the user)

Tell the user the goalposts moved: success is shifting from rank position to **share-of-answer / AI visibility** — being cited inside AI answers, branded mentions, citation clicks — alongside classic rankings. Backlinks dropped to a small slice of algorithm weight; structure, entity clarity, and trustworthy machine-readable content carry more. This reframes what "winning" looks like, so the engine's structural work (which it *can* control) is understood as the high-leverage part.



This module never claims to do off-site SEO (backlinks, brand authority) or to write the content strategy. It makes the artifact *findable and citable*; earning links and authority is another discipline. KPI context for the user: success increasingly means share-of-answer / AI visibility, not only rank position.

## Status

Rendering-in-first-HTML, head essentials, JSON-LD by type, semantics/hierarchy, CWV budget, image hygiene: **MUSTHAVE-BASE**. Open Graph / X Card, answer-first structure, sitemap/robots: **MUSTHAVE-DEFAULT**. `llms.txt` and the share-of-answer KPI framing: **SITUATIONAL / informational** (offered, not forced).
