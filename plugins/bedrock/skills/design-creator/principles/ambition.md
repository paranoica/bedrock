# Ambition — the courage floor

Anti-slop is a *floor against bad*. This file is a **floor against forgettable**. They are equally binding. A page can clear every anti-slop rule, pass every gate, and still be a failure — because it is safe, correct, and unmemorable. That outcome is not "fine, just conservative". It is the most common failure mode of a careful system, and this engine is a careful system, so it is the failure most likely here. Treat timidity as a defect with the same seriousness as slop.

## The core rule (MUSTHAVE-BASE)

**The default posture is ambitious. Justify *down*, never up.**

The engine proposes the awwwards-tier version of the concept first — the one with a real signature moment, a scroll mechanic that enacts the hook, a 3D/canvas/kinetic hero where it fits — and then *dials down* only for a concrete reason (a restraint-domain, an explicit user request, a hard perf constraint). It does **not** start from the safe version and offer to add ambition on request. Leading safe and waiting to be asked for boldness is the timidity this file exists to kill.

If the honest description of a finished page is "a clean, correct landing", that is a fail, not a deliverable. The bar is: **would this place on an awwwards / Godly / FWA gallery?** Not "is it tasteful." Tasteful-and-safe is the median; the median is the thing to beat.

## Where timidity hides (and the counter-move)

| Timid default | What actually happened | Bold default instead |
|---|---|---|
| picked **Clean** because the brief was ambiguous | you removed access to 3D/pin/kinetic to avoid risk | for any expressive brief (brand, marketing, portfolio, launch, product story) **default to Statement**; Clean is a *chosen restraint* for utility/enterprise/accessibility-first, not the safe fallback |
| set **Lean** perf "to be safe" | you pre-banned the one heavy signature moment | default **Balanced** for brand/marketing/launch; Lean is for commerce/utility where speed converts. One heavy hero moment is almost always affordable — budget *for* it |
| shipped **reveal-only** scroll | you called fade-ins "storytelling" | a Statement page needs a real pin / sticky-swap / horizontal / scroll-tied moment (`storytelling.md`) — reveal alone already fails QA |
| satisfied the hook **structurally** and stopped | the hook is real but inert — nothing moves, nothing surprises | enact the hook: it should be *experienced*, not just laid out. A clever static idea is a starting point, not the finish |
| chose the **lightest path** ("90% of the effect") | you rationalized away the signature moment | the light path is the fallback, not the default. Use it when perf genuinely forces it, not because it's easier |
| "I'll **surface the trade-off** and let the user pick" | you led with safe and made boldness opt-in | propose bold *as the default*, offer the lighter version as the fallback. The user dials down, not up |

When you catch any of the left-column thoughts, that is the tripwire — the same anti-rationalization discipline as anti-slop, pointed the other way.

## What "ambitious" means (not "heavy for its own sake")

Ambition is **intentional risk**, not gratuitous load. It can be a single, perfectly-executed bold move — a kinetic hero, a pinned build, a generative canvas, a horizontal chapter, a scroll-scrubbed object, a type system that behaves like an actor. One genuine showpiece beats five tasteful gestures. The point is a moment the visitor remembers and describes to someone — the "tell test" (`concept.md`) raised from a question into a requirement.

This does **not** override the real constraints: accessibility, the domain-fit guard (don't put a circus on a bank — but a bank can still be *bold within restraint*, see Vault-style structural confidence), reduced-motion alternates, and a genuine (not reflexive) perf limit. Ambition is gated by those — and by nothing else. It is **not** gated by the engine's own caution.

## Restraint is a choice, not a default

Some briefs genuinely call for calm: a utility, an enterprise dashboard, an accessibility-first tool, a grief/medical context. There, restraint *is* the ambitious-correct answer and Clean is chosen on purpose. The rule is not "everything must be loud" — it is "the engine must **decide** the intensity against the brief, and its bias when expression is welcome is toward bold." A timid default dressed up as "tasteful restraint" on a brief that wanted a showpiece is the failure.

## Status

The courage floor — ambitious by default, justify down not up, timidity treated as a defect equal to slop, the "would it place in a gallery" bar, propose-bold-offer-fallback: **MUSTHAVE-BASE**. Recorded in `invariants.md` and checked at the QA gate. Gated only by accessibility, domain-fit, reduced-motion, and genuine perf limits — never by the engine's own caution.

**How the bar is actually judged.** "Would it place in a gallery" is not left as a vibe — `tools/ambition-check.md` makes it accountable: decompose into binary proxies (named signature, focal stack depth, non-default composition, enacted hook, not-a-repeat), then a distractor-guarded pairwise comparison against the `references/` exemplar, then a fresh-context re-judgment that must agree, then calibration against the owner's real reactions over time (`tools/calibration.mjs`). The verdict is reported as judgment with its grounding, never as a measured fact. This is what keeps the floor from collapsing into "the model felt good about it".
