# tools/verify.mjs — the gate's real eyes

One-time setup (in the project, or globally next to the skill):

```bash
npm i -D playwright axe-core
npx playwright install chromium      # one download; without it the script self-labels "UNVERIFIED"
```

Run it on a built page or the mockup file:

```bash
node verify.mjs http://localhost:5173            # a preview server
node verify.mjs .design/mockups/v3/index.html    # a static mockup
node verify.mjs dist/index.html --out .design/verify
```

It writes `.design/verify/verify-report.json` and screenshots, and prints a summary.

## What the gate reads (teeth)

- `summary.verdict`:
  - `MEASURED_PASS` — every measurable check is green. **Not fully green yet** — the
    `visual_required` list still has to be done by looking at the PNGs.
  - `MEASURED_FAIL` — at least one measured check failed (`blocking_failures` lists them); the gate is red.
  - `UNVERIFIED` — no browser; checks are labelled, **never passed**. Ship marked "requires render".
- `build_hash` — freshness binding. If it doesn't match the current build, the report is
  stale and the gate must reject it (stops "I ran it earlier").
- Exit code: `0` measured-pass · `1` measured-fail · `3` no browser.

## Three tiers, on purpose

- **measured** — axe a11y (serious/critical), 320px overflow, CLS, LCP. Script decides.
- **visual_required** — what only eyes can judge: hierarchy, optical balance, hook
  realized, slop tells, ambition; plus contrast that axe marks *incomplete* (text over
  photo/gradient/glow). The model must LOOK at the screenshots for these.
- **unverified** — emitted only when there's no browser. A report that claims all-green
  with `browser: false` is a contradiction the gate rejects.

INP is not measured headlessly (needs real interaction) — profile it in a live session if it matters.
