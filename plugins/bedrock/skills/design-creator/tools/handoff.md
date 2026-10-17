# Handoff — design-creator ⇄ code-review

The two skills make each other's output safer and better: design-creator ships real code that
should be reviewed for fatal/security/a11y/perf bugs; code-review, when it hits design/frontend
issues, can route them back to the design engine. This file defines the contract so they
cooperate **without looping**.

## Direction 1 — design-creator → code-review (Stage 3.5, automatic, terminal)

After Stage 3 (design-to-code) passes design-QA + the critic, and **only when real code was
produced** (skip for mockup-only / Stage-1 stops), run a ship gate:

**Spawn code-review as an isolated subagent in review-only mode:**
```
Task(subagent_type: "general-purpose",
     prompt: <contents of the installed code-review SKILL.md>
             + "MODE: review-only. Scope: the files I just generated: <paths>.
                HANDOFF=design-creator, depth=1, DO NOT hand off to any other skill,
                DO NOT auto-fix — return findings only.
                Focus the review on: fatal/security bugs, frontend safety, accessibility
                (axe/contrast/focus/semantics), performance (CWV, bundle, render cost),
                and supply-chain on any deps you added.")
```
Why a subagent and not an in-context call: the review's heavy checklists stay out of the design
session, and the two skills' instructions don't co-mingle. The subagent returns a findings
report; **design-creator applies the fixes itself** (or surfaces them to the user if they're
design trade-offs), then re-runs the design-QA gate on the fixed code.

This catches what design-QA doesn't: real exploitable bugs, dependency CVEs, removed defenses,
data-flow issues — the things that make a beautiful site also a safe one.

## Direction 2 — code-review → design-creator (suggest-only, user-gated)

code-review **never** auto-launches the design engine. When its findings are dominated by
design/a11y/frontend-UX issues (or the user is clearly working the visual layer), it **offers**:
"several of these are design/accessibility issues — want me to hand them to `/design-creator`
with a scoped prompt (e.g. 'fix focus-visible + contrast + the unstyled form controls in the
checkout flow')?" — and waits. Only on the user's yes does it hand off, passing a scoped prompt.

## The loop guard (why this can't ping-pong)

- **Asymmetry:** D→R is automatic but *terminal* (review returns a report, launches nothing).
  R→D is *suggest-only* (needs the user). So there is no automatic round trip.
- **Depth flag:** every handoff prompt carries `HANDOFF=…, depth=1, DO NOT hand off`. A skill
  invoked as a handoff must **not** initiate another handoff. If you receive a prompt containing
  a `HANDOFF=` line, you are the leaf — review/fix and return, don't delegate onward.
- **Subagents can't spawn subagents** (Claude Code), so a review running as a subagent
  physically cannot launch the design engine even if it wanted to.

## If the skills aren't both installed

The ship gate is best-effort: if code-review isn't available, design-creator says so once
("code-review skill not found — shipping without the external safety pass; install it for the
fatal-bug/a11y/security review") and proceeds. It never blocks the deliverable on a missing
companion skill.
