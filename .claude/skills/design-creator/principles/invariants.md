# Invariants — the card that gets re-read, not remembered

This is the short, load-bearing core of the engine. It is deliberately tiny so it can be **re-read before every generation step and at every QA gate** without cost. In a long session, instruction-following decays as context fills (the "curse of instructions" / lost-in-the-middle / context rot). The cure is not willpower — it is keeping this list short and re-injecting it. If a rule is here, it is non-negotiable and survives any amount of conversation.

## How to use this file

1. Read it at the start of each stage, before writing any section's code, and at the top of every `design-qa.md` run.
2. Do not assume you "already know it" because you read it earlier in the session. Re-read.
3. Durable project state (tokens, decisions, ledger) lives in `.design/` files, not in your memory of the chat — re-read those on demand too (see `index.json` → `state_files`).

## The invariants

1. **Hook first.** Every site is built around one stated hook (`concept.md`). No hook → incomplete deliverable.
2. **Anti-slop floor holds always** (`anti-slop.md`): no Inter/Roboto as display voice, no purple-as-default accent, no pure `#000`/`#FFF`, no browser-default form controls, no emoji, no thoughtless dot+pill+mono-caps badge.
3. **Accent ≤ ~10% of the screen** unless the chosen family explicitly overrides it (then the override is stated).
4. **One source of light.** Shadows, highlights and gradients on every surface agree on where the light is (`depth.md`).
5. **60fps only.** Animate `transform`/`opacity`; every state change animates, never snaps; `prefers-reduced-motion` has a designed static alternate, not a bare "off".
6. **Accessibility is non-negotiable** (`accessibility.md`): `:focus-visible`, contrast ≥ 4.5:1 / 3:1, touch targets ≥ 44px, semantic HTML + heading hierarchy.
7. **The QA gate is blocking and measured, not self-attested** (`design-qa.md` + `tools/verify.md`). Runtime checks (contrast over real backgrounds, 320px overflow, CLS) are verified by rendering + screenshot, not by reading code.
8. **Match the deliverable type.** A landing, an app surface (dashboard/auth/profile), and a lone component are judged by different gate branches. Do not demand a scroll-storytelling spine from a login form.
9. **On an existing project, conform before improving.** Read the project's de-facto tokens and obey them (`adopt.md`); do not impose a new hook/mode/archetype unless explicitly asked.
10. **Aesthetic must fit the domain.** Don't put playful brutalism on a bank/clinic/enterprise (`aesthetic-families.md` → domain-fit guard).
11. **Never fabricate social proof.** No invented testimonials, metrics, client logos. Use placeholders marked "needs real content".
12. **Governance — never do these silently** (`governance.md`): delete the user's mockup history, overwrite a `CLAUDE.md`, ship a destructive action without confirmation, or pass off a guess as grounded.
13. **Flag confidence.** When a choice is a guess (no brand input), say so in the narrative ("palette is a guess — no brand assets given").
14. **Ambition is a floor, not a bonus** (`ambition.md`). The default posture is bold: propose the gallery-tier version and justify *down*, never lead safe and add boldness on request. A correct-but-forgettable page is a failure equal to a sloppy one. Gated only by accessibility, domain-fit, reduced-motion, and genuine perf limits — never by the engine's own caution.
15. **Green gates prove grounding, hygiene, and variety — not taste.** `verify.mjs` measures contrast/overflow/CLS; `spread.mjs`/`diversity.mjs` guarantee the batch is *different*, not *good*. A result that passes every gate but is forgettable is still a failure (ties to 14). And a best-of-N where the whole batch is weak is the **weak-batch guard**: regenerate or escalate — never ship the least-bad. Diverse-but-mediocre is mediocre.

## Anti-rationalization

These rules fail in one specific way: under pressure to please or to "just ship", the engine quietly reframes a violation as acceptable. That reframing **is the signal to stop**, not a reason to proceed.

| If you catch yourself thinking… | The honest reading is… | Do |
|---|---|---|
| "a small status pill is fine here, it's basically informative" | you are about to build the banned AI badge | express the status as real typography or a function, not a dot+pill |
| "the gate's storytelling check is failing, I'll just relax it" | you are skipping the gate | check the deliverable-type branch; if it's truly an app surface, the check doesn't apply — otherwise fix it |
| "the user will love this, the contrast is close enough" | you are self-attesting a measurable fact | render and measure (`tools/verify.md`) |
| "this brutalist look is bold, the bank will stand out" | you are mismatching aesthetic and domain | run the domain-fit guard |
| "I'll invent a testimonial, it reads better" | fabrication | placeholder marked "needs real content" |
| "I already read the rules, no need to re-check" | context has moved on since then | re-read this file |
| "I'll pick Clean / Lean to be safe" | you are removing access to the bold version before proposing it | for an expressive brief default to Statement/Balanced; choose restraint only for a concrete reason (`ambition.md`) |
| "the hook is there in the layout, that's enough" | the hook is inert — nothing moves or surprises | enact it; a static clever idea is the start, not the finish |
| "a clean correct landing is a fine result" | you shipped the median | ask "would it place in a gallery?"; if no, it's a timidity fail, not a deliverable |
| "I'll surface the trade-off and let them choose" | you led safe and made boldness opt-in | propose bold as default, offer the lighter fallback |

When the reframing appears, treat it as a tripwire: stop, name the rule, comply.
