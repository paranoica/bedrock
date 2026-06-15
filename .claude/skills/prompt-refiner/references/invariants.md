# Invariants — re-read before classifying a request and before sharpening

The compact non-negotiable core. Short by design.

1. **Residue-only.** Activate only when no profile engine (design-creator / code-review / genesis)
   resolves and can start as-is (`residue-gate.md`). Reading a request to classify it is **cheap,
   silent, and NOT activation** — refiner is visible to the user only on a **residue** verdict.
2. **Default-yield on doubt.** Borderline whether an engine could start → **yield to the engine, stay
   silent**. False silence is cheap (the engine asks its own question); false interception is costly.
3. **Managed-project rule.** In a genesis-managed repo (`docs/` + `genesis.tasks.json`), a feature /
   new-work request resolves to **genesis (replan)** — never sharpen a feature straight to code around
   the backlog (that is the desync the anchor mechanism prevents). Non-managed repo → sharpen directly.
4. **Sharpen, then route.** Refiner turns residue into a precise CC-prompt and routes it to the engine
   it now resolves to (or direct execution). It does **not** do the work an engine owns.
5. **Discover before you ask.** Default to act + discover via tools. Ask **≤1** clarifying question
   only when interpretations diverge into materially different / irreversible work exploration can't
   settle. **Yield (take-or-not) and question (post-take sharpening) are separate branches — never
   both on one request.**
6. **Quiet + cancelable.** Sharpen silently; never narrate the refinement. One word from the user
   cancels and refiner steps fully aside.
7. **Output = the CC-prompt schema.** One task + explicit files + acceptance + verify handle +
   reference pattern (+ for bugs: symptom + likely location + definition-of-fixed) + anti-overengineering
   clause. **No prefills** (deprecated on Claude 4.6+; they error).
8. **Leak rule.** If refiner ever takes what an engine could have started, the residue-test leaked —
   fix the test, don't add a special-case rule.
