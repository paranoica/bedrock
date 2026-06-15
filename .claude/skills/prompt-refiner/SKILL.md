---
name: prompt-refiner
version: 0.1.0
description: Last-resort catcher for VAGUE requests that no other skill clearly owns. Use only when a request is too underspecified to act on and does not resolve to design-creator (visual layer), code-review (audit existing code), or genesis (start/plan a project) — e.g. "fix this", "make it work", "do something about X", "это надо переделать", "разрули", "почини". Turns vague residue into a precise, routed Claude Code prompt (one task, files, acceptance, a verification handle), asking at most one clarifying question and only on genuine ambiguity. Quiet and cancelable; it DEFERS to any profile skill that can start as-is, and stays silent otherwise.
---

# Prompt Refiner

Catches the residue — the "fix this / make it work / do something about X" mush that falls through
every profile engine — and turns it into a precise prompt, routed to whoever should run it. It is the
**last resort**, not a layer in front of everything.

## Read this first, every time
1. **`index.json`** — router + state map.
2. **`references/invariants.md`** — the non-negotiable core (residue-only, default-yield, managed-rule,
   quiet+cancelable). Re-read before classifying a request and before sharpening.

## Activation boundary — the FIRST thing you do (and usually the last)

Run the **residue-gate** (`references/residue-gate.md`) before anything else:

1. **Classify resolvability — cheaply and SILENTLY.** Reading the request to decide which engine it
   resolves to is *not* "running the refiner" and costs the user nothing. You become visible only on a
   **residue** verdict.
2. **Resolves to one engine that can start as-is?** (vague *within* an engine still resolves — the
   engine surveys/asks its own question.) → route there, **stay silent**.
   - design-creator: build/redesign a visual surface · code-review: audit/debug locatable code ·
     genesis: project inception/planning, **or** a feature in a **genesis-managed** repo (`docs/` +
     `genesis.tasks.json`) → genesis **replan** (never sharpen a feature around the backlog).
3. **Doubts?** **Default-yield** — hand it to the engine and stay silent. False silence is cheap; false
   interception is costly.
4. **Only if no engine resolves/starts** (doubles between engines, or no target) → **take it**:
   discover via tools, sharpen into the CC-prompt schema (`references/refine-algorithm.md`), ask ≤1
   question only on material divergence, and route the sharpened prompt.

If the residue-gate yields, you produce **no output** — the owning skill takes over. That silent
deferral is the common case.

## What it does when it takes
Sharpen silently → one task + explicit files + acceptance + verify handle + reference pattern (bugs:
symptom + likely location + definition-of-fixed) → re-resolve → route to dc / code-review / genesis /
direct execution. Cancelable in one word. Details: `references/refine-algorithm.md`.

## Working language
Skill files are English. The (rare) clarifying question is asked in the **user's language**.

## What this skill does NOT do
- Does not act as an ambient layer in front of every request — it is invisible unless the verdict is residue.
- Does not do an engine's work — it sharpens and routes.
- Does not sharpen a feature around a genesis-managed backlog — that routes to genesis replan.
- Does not narrate its refinement, and never blocks: one word cancels it.
