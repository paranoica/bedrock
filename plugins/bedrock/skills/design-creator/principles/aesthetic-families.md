# Aesthetic Families

The **character axis** of the design — independent of (orthogonal to) the mode/intensity axis. A family answers "what character"; the mode answers "how intense". "Cinematic dark in Clean" and "cinematic dark in Statement" are both valid.

## The families

These are starting characters, not a closed list — chosen in survey Q1:

- **Editorial minimalism** — calm neutrals, serif or narrow-grotesque headlines, generous line-height, single accent. Reading-first.
- **Cinematic dark** — film-grade dark, oversized type, motion-forward, media-heavy hero.
- **Warm editorial** — terracotta / cream / clay, serif body, human and approachable.
- **Terminal-core** — monospace, phosphor or amber on near-black, hard edges, CLI metaphors.
- **Data-dense pro** — charts are the hero, tight spacing, fixed-width numerals, dark-first.
- **Playful color** — high saturation, rounded corners, decorative shapes, consumer-friendly.
- **Glass / soft-futurism** — frosted blur, layered translucency, soft gradients.
- **Neon-brutalist** — hard edges, deliberate type mixing, oversized numerals, a single saturated hue striking a monochrome base.

## How a family is used

The family sets the default character of color, typography, motion, and decoration. The engine does not clone any specific brand — families are characters we apply originally. Reference brands may be looked at for ideas; their concrete design files are never copied (copyright, and cloning produces generic output).

## Family × mode

The family chooses the character; the mode chooses the intensity; intensity-by-hierarchy distributes that intensity within a page. Three axes of control, two-mode simplicity.

## Domain-fit guard (MUSTHAVE-BASE)

Character is not free — it must fit what the domain's audience reads as trustworthy. A family that signals "bold and experimental" reads as *unsafe* on a product where polish signals safety. Before committing a family, check it against the domain:

- **Creative / fashion / portfolio / consumer-playful / culture** → the loud families are at home: neon-brutalist, tactile-brutalism, playful color, Y2K, maximalist. Differentiation is the job.
- **Finance / banking / fintech / healthcare / legal / enterprise B2B / security** → conventional polish *is* the trust signal. Default to editorial minimalism, data-dense pro, cinematic-restrained, warm-editorial. A playful or brutalist treatment here actively erodes credibility, however "bold" it looks in isolation.
- **In-between (SaaS, dev tools, marketplaces)** → a restrained version of a characterful family (terminal-core in Clean, cinematic-dark in Clean) usually wins — personality without spooking the buyer.

The guard is a question the engine answers before the narrative, and states: "family X fits domain Y because…". If the bold family the hook wants conflicts with a trust-sensitive domain, surface it to the user rather than shipping a mismatch. This is recorded as an invariant (`invariants.md` #10). Matrix, not a hard table — judgement against the specific brief — but the engine never picks a domain-inappropriate family silently.

## Expanded family vocabulary (use deliberately, fit the domain)

Beyond the core families, these are valid characters to reach for when the hook and domain call for them — each with a one-line "what it signals" so it's chosen, not defaulted:
- **Swiss / international** — grid, Helvetica-lineage, objective; trust, editorial, institutional.
- **Tactile brutalism** — raw structure but *refined* (not the lazy neon kind): heavy type, visible grid, restrained palette; confident, design-literate brands.
- **Y2K / techno-optimist** — chrome, gradients, early-web nods; culture, music, youth.
- **Organic / humanist** — soft shapes, hand elements, warm neutrals; wellness, craft, food.
- **Editorial / print-inspired** — magazine layout, drop caps, strong measure; long-form, publishing, thought leadership.
- **Riso / print-artifact** — limited spot colors, misregistration texture; indie, creative, events.

Each still passes the domain-fit guard above. Reach for these to *differentiate*, never to decorate.
