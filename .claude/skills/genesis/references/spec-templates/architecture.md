<!--
TEMPLATE — genesis fills this into docs/architecture.md, parametrized.
Rules:
- The "Invariants" section is a must-anchor section: each invariant is an arch:<slug> atomic unit.
  arch:* anchors are CROSS-CUTTING (changing one transitively re-checks dependent tasks).
- In ADOPT mode: statements about EXISTING code MUST cite file:line (they are observed facts).
  Rationale that cannot be grounded in code does NOT go here — it goes to open-questions.md as
  inferred/unconfirmed. architecture.md states WHAT is; never an un-grounded WHY.
- Data-model entities map to term:* anchors in glossary.md.
-->
# Architecture — <PROJECT NAME>

> Decided/observed structure. See `decisions.md` for the WHY, `glossary.md` for terms.

## Components
- **<component>** — <responsibility, boundaries, who it talks to>.

## Data flows
- <flow>: <source> → <transform> → <sink>.

## Data model
> Entities are defined in `glossary.md` (term:*). Here: relations, cardinality, status transitions.
- **<Entity>** (`term:<slug>`): <fields that matter> · status transitions: <a → b → c>.

## Invariants
<!-- @anchor arch:<slug> -->
- **<invariant name>** — <a property that must always hold; e.g. "a Booking's payment is idempotent
  per (booking_id, period)">.
