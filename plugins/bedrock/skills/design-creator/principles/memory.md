# Memory — taste profile & sameness ledger

Two durable memories that make the engine feel like it *knows* the owner and doesn't repeat itself by inertia — without overriding any hard rule. Both live in files (`index.json` → `state_files`), are re-read on demand, and never silently change the invariants. Both are advisory inputs, not new laws.

## Taste profile (two levels)

A learned record of the owner's stated preferences, applied as defaults — never as overrides of safety/a11y/anti-slop.

- **Level 1 — owner global** (`~/.claude/design-taste.json`): preferences that hold across projects. E.g. "likes warm-editorial over cold-minimal", "wants magnetic cursor on (taste default-off otherwise)", "prefers serif display", "dislikes heavy 3D". Captured when the owner states a preference, or confirmed when they repeatedly steer the same way.
- **Level 2 — project override** (`.design/taste.json`): per-project taste that **wins over** the global profile. A playful brand can opt into things the owner usually avoids; the project context is more specific, so it takes precedence.

**Resolution order:** invariants/governance (never bend) → project taste → owner-global taste → engine defaults. The profile changes *defaults and proposals*, never the hard floor. The engine states when it's applying a learned preference ("defaulting to a warm-editorial direction based on your saved taste — say the word to go a different way"), so it's transparent and overridable, not a black box.

**Capture discipline:** only record a preference the owner actually expressed or clearly repeated. Don't infer sweeping taste from one ambiguous choice. Never store anything sensitive. The owner can ask what's remembered and clear it.

## Winners → exemplars & anchors (the taste loop)

The taste profile above is *stated preferences*. This is the **revealed-preference** half: when
the owner picks between candidates (the diverse best-of-N of the work loop, or an explicit "which
is better?" pair), log the pairwise vote with `tools/taste.mjs`. Over ~20–50 votes that yields a
Bradley-Terry/Elo **taste vector** (per axis: type-contrast, color discipline, density,
motion-intensity, signature presence) and a set of **owner winners**. Those winners do triple
duty, all advisory, never overriding the floor:
- **generator exemplars** — fed in-context so the *generator* biases toward what this owner keeps
  (work loop "Making the first try land", move 1c);
- **critic anchors** — used as the pairwise comparison target in `tools/critic.md` Tier 3, so
  "gallery-tier?" is judged against *this owner's* bar, not a generic exemplar;
- **critic calibration** — where the critic's pairwise verdict disagrees with the owner's logged
  vote on an axis, down-weight the critic there and escalate that axis to the owner next time
  (the aesthetic judge is weakest exactly on "interesting", so it must know when to ask).
Cold-start (no votes yet) falls back to the curated exemplars + the 2–3 direction pick.

## Sameness ledger (soft flag + favorites)

A per-project record (`.design/ledger.json`) of what's already been used — hashes/short descriptors of hooks, archetypes, hero mechanisms, palettes, signature devices.

- **Soft flag, not a ban.** When a new build reaches for the same hook-mechanism or archetype as a previous one *in this session/project without a reason*, raise a quiet flag: "this is the third pin-section reveal — intentional, or reaching for it on autopilot?" The engine then either justifies the reuse or varies it. Inertia-repeats get caught; deliberate consistency does not.
- **Favorites pin.** The opposite case is real too: the owner can **pin** a device as "this is our thing, keep using it" (a signature, a palette, a motion curve). A pinned device is exempt from the sameness flag — repetition there is brand consistency, not slop. This is the explicit answer to "don't punish me for being consistent on purpose".
- Distinguish the two: unpinned + repeated-without-reason → flag; pinned → encouraged; varied → fine.

## Status

Taste profile (two-level, advisory, transparent, never overrides the floor) and the sameness ledger (soft flag + favorites pin): **SITUATIONAL** infrastructure — active when persistent state is available, silently skipped when it isn't. Neither ever overrides invariants, governance, or accessibility.
