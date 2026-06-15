# Design handoff — genesis → design-creator

genesis owns **what** the product is and its scope; design-creator owns **how it looks**. The handoff
is a **closed, structured brief** and it is leak-proof **by construction**: the schema has **no field**
for a hook, concept, narrative, aesthetic, mode, or palette. There is nothing to leak into.
design-creator forms its own hook — feeding it rich prose collapses its output diversity (its own
docs say so: `design-creator/principles/anti-slop.md:62`, `concept.md:34-42`, `SKILL.md:91`).

**A `design-brief` is emitted ONLY for a project with a real visual web surface** (project-type
web-app / dashboard). For a CLI, library, API, or worker, genesis emits **no brief** — design-creator
is web-visual-only, so there is nothing to hand it.

## The design-brief — the ONLY keys genesis emits

Written to `.genesis/design-brief.json`. **Closed key set** — any other key is a contract violation:

```jsonc
{
  "domain":      "<one noun phrase: what kind of product>",     // "storage-unit rental marketplace"
  "audience":    ["<who uses it>", "..."],                       // ["renters", "unit owners"]
  "surfaces": [                                                  // page/screen inventory (from interview)
    { "name": "<surface>", "purpose": "<the job this surface does>",
      "key_states": ["<state>", "..."] }
  ],
  "in_scope":    ["<surface/feature in MVP>", "..."],
  "out_scope":   ["<explicitly out>", "..."],
  "tone":        ["<adjective>", "..."],                         // CONSTRAINED: 1–4 adjectives, NOT prose
  "brand_assets":["<path/to/logo|font|palette-if-given>", "..."] // paths only; absent → dc decides
}
```

## Why each guard exists (the leak-proofing)

- **No `hook` / `concept` / `narrative` / `aesthetic` / `mode` / `palette` key.** The **absence is the
  guarantee.** A field marked "do not fill" gets filled by someone; a field that does not exist cannot
  leak. This is the by-construction version of the rule, not a reminder.
- **`tone` is a short adjective list, never prose.** A free-text tone is the back door a narrative
  sneaks through. Cap it at 1–4 adjectives (e.g. `["calm","trustworthy"]`). If more nuance is wanted,
  that is design-creator's survey to run — not genesis's to pre-empt.
- **`surfaces` is the shared scope inventory** (page list / audience / states). genesis owns it as
  *inventory*; it is consumed without re-asking — and without being told how it should look.
- **`brand_assets` are paths only.** genesis passes what the user gave (logo, fonts); it does not
  describe or interpret them.

## How the brief is consumed (file-as-message between agents, not an autonomous reader)

design-creator is vendored **unchanged** — it has **no code that reads `.genesis/design-brief.json`**.
The brief is consumed by the **agent invoking design-creator**: that agent reads the brief and feeds
the fields into design-creator's own survey as *already-known answers* (domain, audience, surfaces,
in/out scope, tone), so the survey does not re-ask them. design-creator still forms its own hook. So
the handoff is a structured **message passed via a file**, not an interface design-creator ingests on
its own — don't assume it is tighter than that.

## Enforcement (structural guarantee + discipline — be precise about which is which)

The **structural** guarantee is the schema itself: it has **no `hook`/`concept`/`narrative`/aesthetic
field**, so there is nothing for a hook to leak *into* — that part is genuinely by-construction. The
rest is **genesis discipline**: it emits exactly these keys and no prose direction. There is **no
runtime validator script today** (don't claim one) — if you want hard enforcement, validate
`.genesis/design-brief.json` against this closed key set before invoking design-creator.
