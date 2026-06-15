# Concept — The Hook

The single most important file for making a design **memorable** rather than merely competent.

## The problem this solves

Avoiding slop (anti-slop, the palette ladder, the typography stack, the status system) protects the **floor** — it stops the output from being bad. But a floor is not a ceiling. A site can clear every anti-slop rule and still be forgettable: correct, tasteful, and indistinguishable from ten other correct, tasteful sites.

The missing piece is a **hook** — one bold, specific, central idea that this particular site is built around. Not a palette, not an aesthetic family, not a layout level. A *concept*. The one thing a visitor remembers and describes to someone else.

## The rule (MUSTHAVE-BASE)

Before any code is written, the engine **must** formulate the hook for this specific site: a single concrete conceptual move that distinguishes it from any other site in the same niche. One. Specific. Stated in a sentence.

Then **the whole page is built as the expression of that hook.** Every section either advances the hook or stays deliberately quiet so the hook lands. The hook is not a decoration in the hero — it threads through the entire page.

## What a hook is — and is not

A hook is **not**:
- an aesthetic family ("cinematic dark") — that is character, shared by thousands of sites,
- a palette or a font choice — that is execution,
- a list of nice features (marquee + 3D + bento) — that is an inventory, not an idea.

A hook **is** a concept that reframes the page. Examples (illustrative — invent a new one each time, never reuse these):
- A coffee roastery built around the **roast date as the hero** — the date is huge, it is everywhere, it is the product.
- A dev-tool whose entire site behaves like **one continuous terminal** — you do not scroll, you "enter commands".
- An architecture studio about light, where **light physically travels across the page** as you scroll — the concept is enacted, not described.
- A archive site where the page is **organized as a physical card catalog** the visitor pulls through.

The test: can the hook be stated in one sentence, and would that sentence make someone curious? If the honest sentence is "it is a dark landing page with big type" — there is no hook yet. Keep going.

**A stated hook is the start, not the finish — enact it.** A hook that only exists as a clever static layout is inert. The page should let the visitor *experience* the hook (it moves, builds, responds, surprises), not merely read it laid out. Satisfying the hook structurally and stopping there is the timidity failure (`ambition.md`): the idea is real but nothing happens. Reach for the version that would place in a gallery, then dial down only for a concrete reason.

## Finding the hook without collapsing to the median (Verbalized Sampling)

The first hook a model offers is the *typical* one — mode collapse toward the most-probable
idea, which is the median, which is forgettable. Counter it explicitly: before committing,
**generate a handful of candidate hooks (4–6) together with a rough likelihood for each**, then
**deliberately pass over the top-probability one** and pick from the interesting tail — the
candidate that is specific, enactable, and would make someone curious. This is training-free
and is the single cheapest move against generic concepts. The mechanism-variety rule below then
applies to the chosen candidate.

## How the hook is found

1. Look at the product's **deepest truth** — what it genuinely is about, the thing the founder cares about most.
2. Find a way to make that truth **structural** — expressed by how the page is built, behaves, or is navigated, not stated in copy.
3. Commit. One hook, not three. A site with three "fishки" has none.
4. Make it **specific to this product** — a hook that could be lifted onto a competitor's site is too generic.

## The hook must not collapse into one mechanism

There is a trap: every hook becomes "an object that morphs as you scroll down the page". A glass that fills, a chair that assembles, a constellation that draws, a route that traces — these are the *same mechanism* wearing different costumes. If every project gets a scroll-driven vertical morph, the hooks are no longer distinct; the sameness just moved from the skeleton into the gimmick.

So the hook's **mechanism** is chosen as deliberately as the hook itself, from a range — scroll-morph is only one option:

- **Scroll-driven transformation** — something changes as the page is scrolled. Powerful, but overused; pick it only when vertical progression genuinely *is* the metaphor (a journey, a process, time passing).
- **Cursor / pointer interaction** — the thing responds to where the visitor points; the hook lives in active play, not passive scroll.
- **Reframed navigation** — the *way you move through the site* is the hook (an index pulled like a card catalog, a map you traverse, chapters you turn).
- **A living system** — something runs on its own: a simulation, a generative pattern, a clock, a state that evolves with real time, not with scroll.
- **Structural / typographic** — the hook is in the page's bones: a layout that does something no other site does, type that behaves as an actor, a grid with a concept.
- **Content-as-mechanism** — the real data or content drives the form (the actual catalogue reorganises, real numbers reshape the page, the inventory *is* the layout).
- **Input / participation** — the visitor gives something (a choice, a word, a value) and the page answers; the hook is a small two-way moment.

Across a set of projects, the mechanisms must vary. Two hooks built on the same mechanism in one session is a flag — the same failure as two identical skeletons.

## Where the hook lives in the pipeline

- **Survey** — after the aesthetic family and mode are set, the engine works out the hook (drawing on the project context answers) and states it.
- **Narrative (work-loop step 2)** — the narrative MUST include an explicit line: "the hook of this site is —". The user sees it and approves it at the gate. Uniqueness is art-directed and confirmed *before* code, exactly like the rest of the narrative.
- **patterns/** — each section recipe's section 7 ("how the hook shows up here") forces the hook through every section, not just the hero.
- **design-QA** — a binary check is added: "is the stated hook actually realized — yes/no". A site that lost its hook in execution fails QA.

## Relationship to the other axes

- Aesthetic family = character. Mode = intensity. **Hook = idea.** Three independent things.
- The hook is realized *through* the family and mode — a light-travels-down-the-page hook looks one way in editorial-Clean, another in cinematic-Statement — but the hook itself is chosen first and is what makes the site that site.

## Status

The hook requirement — formulate one, state it in the narrative, build the page around it, verify it in QA — is **MUSTHAVE-BASE**. A site shipped without an identifiable hook is an incomplete deliverable, not a stylistic choice.
