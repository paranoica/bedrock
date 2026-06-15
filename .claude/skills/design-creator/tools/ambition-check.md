# ambition-check — grounding the "is it gallery-tier?" judgment

`ambition.md` sets the floor (bold by default, forgettable = defect). This file makes the
verdict **less of a vibe and more auditable**. You cannot make taste objective, but you can
cut the variance and label what's measured vs judged. The QA gate's ambition check runs
this, not a bare "does it feel good".

Why this shape (grounded in LLM-judge research):
- Absolute "rate this 1–10 on boldness" scores drift — a single judge has no stable internal
  scale. So we **don't** score in the abstract.
- **Pairwise** ("is this in the tier of the reference, or weaker?") agrees with human
  preference far better — but it's **gameable by distractor features**: a flashy-but-empty
  page (more motion, more 3D) can fool a comparative judge the same way verbosity fools text
  judges. So pairwise alone is unsafe for design, where "more effects" is the obvious distractor.
- The fix is to **decompose into binary sub-decisions first** (robust, hard to game), then
  do the pairwise call **anchored on those sub-decisions**, then **reduce variance** with a
  fresh-context repeat, then **calibrate** against the owner's real reactions over time.

## Step 1 — Decompose the vibe into countable proxies (binary, do these first)

Answer each yes/no against the rendered screenshots (`tools/verify.mjs` output), not the source.
"Gallery-tier" is unmeasurable whole; these parts are not:

1. **Signature device present.** Is there ≥1 *named* signature technique — the specific thing
   someone would remember (a kinetic headline, a scroll-driven reveal, a real 3D/canvas
   moment, a distinctive nav, a bespoke cursor interaction)? **Name it and point to where it
   renders.** Zero named signatures → ambition FAIL. ("It has nice spacing" is not a signature.)
2. **Focal technique-stack depth.** On the focal element (usually the hero), how many *distinct*
   techniques are stacked — type treatment + motion + depth/light + composition + a point of
   view? A bare correct hero stacks ~1. A memorable one stacks several. < 2 on the focal
   element → likely timid.
3. **Composition is non-default.** Is there any asymmetry, scale jump, broken/överlapping grid,
   or deliberate negative space — or is it the centered-single-column / uniform-card-grid slop
   tell? All-default composition → FAIL the proxy.
4. **Hook is enacted, not inert.** The stated hook (`concept.md`) does something — it moves,
   reveals, responds — rather than just sitting in the layout. A clever static idea is the
   start, not the finish.
5. **Not a repeat.** Cross-check `.design/ledger.json` (sameness ledger): are the archetype,
   hook-mechanism, and palette reuses of a recent project? Repeats correlate with forgettable;
   a repeat must be a deliberate pinned favorite, not inertia.

A result that fails proxies 1, 3, or 4 is **timid-but-correct slop** regardless of how clean it
is. These three are the load-bearing ones.

## Step 2 — Pairwise against the reference, anchored on Step 1

Place the output next to the matching exemplar in `references/` (clean-exemplar for Clean mode,
statement-exemplar for Statement). Ask the **comparative** question, but tie it to the proxies so
a flashy-empty page can't win on distractors:

> "Compared to the exemplar, is this in the same tier? Judge on: signature strength, focal depth,
> compositional intent, and hook enactment — NOT on raw amount of motion/effects."

Rules:
- **Control position bias:** make the call both ways (output-vs-exemplar and exemplar-vs-output);
  if the two disagree, treat it as "not clearly in-tier" → does not pass.
- **Distractor guard:** if the output only wins because it has *more* effects (not better-aimed
  ones), that's the distractor trap — it does not pass. More ≠ bolder; intentional = bolder.
- Verdict ∈ {in-tier, below-tier}. Below-tier on an expressive brief → ambition FAIL.

## Step 3 — Reduce variance (the judgment is where the noise lives)

The subjective call is exactly where a single pass is unreliable, so don't trust one pass:
- Re-make the Step 2 verdict in a **fresh context** that sees only the screenshots + the Step 1
  proxy results — not your own justification for the design (so it can't anchor on your intent).
  In Claude Code this fresh-context pass **is** the `tools/critic.md` subagent (the gate spawns it on every result); in chat, re-derive deliberately.
- If the two verdicts disagree, the honest reading is **below-tier** (unstable ⇒ not earned).
- This is self-consistency / a 2-judge panel — cheap, and it catches the cases where the first
  pass was just being agreeable.

## Step 4 — Calibrate against reality over time

Taste won't become objective, but you can learn whether *this* engine's "in-tier: yes" calls
actually track the owner. When a result is resolved by the user — "love it", "meh", or picking
v2 over v1 — record the engine's pre-judgment vs the outcome:

```bash
node tools/calibration.mjs record <predicted_in_tier 0..1> <outcome 1|0>
node tools/calibration.mjs report      # Brier score + calibration table
```

Over time the Brier score says whether "in-tier" means what it claims. A poorly-calibrated
engine (says in-tier, owner keeps saying meh) should raise its bar; well-calibrated → trust it
more. This closes the loop the taste-profile/ledger left open.

## Step 5 — Label it as judgment in the output

Never present the aesthetic verdict as a measured fact (that's the same lie `verify.md` forbids
for rendering). State it as judgment, with its grounding:

> **Ambition:** in-tier vs statement-exemplar (2/2 fresh-context passes agree). Signature:
> scroll-driven type-mask in the hero. Focal stack: 3 (kinetic type + parallax depth + asymmetric
> grid). Hook enacted. Not a ledger repeat.

The user then sees exactly which parts are facts (Step 1 proxies, the render numbers) and which
is the model's taste (the pairwise tier call) — same honesty contract as the rest of the gate.

## How the gate uses this
`design-qa.md`'s **Ambition** check = Steps 1–3 pass (proxies hold, in-tier, stable). A FAIL
blocks the result like any other gate check. Step 4 runs at resolution time; Step 5 is how the
verdict is reported. On a deliberately-restrained brief (Clean/Lean for a real reason), the bar
is "is the restraint intentional and excellent", not "is it loud" — but it still must clear
proxies 1, 3, 4 in their quiet register (a Clean page still needs a signature, intent, and an
enacted hook; it just expresses them calmly).
