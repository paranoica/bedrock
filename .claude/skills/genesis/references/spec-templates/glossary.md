<!--
TEMPLATE — genesis fills this into docs/glossary.md, parametrized.
Rules: every domain term is an anchored atomic unit (term:<slug>). A term used anywhere in
decisions.md or a task's acceptance MUST be defined here with an anchor. This whole file is a
must-anchor file: mixed anchored/unanchored entries = CRITICAL (partial annotation).
term:* anchors are CROSS-CUTTING — redefining one transitively re-checks every task that depends
on it (directly or via a decision that refs it).
-->
# Glossary — <PROJECT NAME>

> Unambiguous domain vocabulary. **If code uses a term differently, that is a bug.**

<!-- @anchor term:<slug> -->
**<Term>** — <one-paragraph unambiguous definition. Include the status enum if the term is a
stateful entity, e.g. "status ∈ {pending, active, ended}".>

<!-- @anchor term:<slug> -->
**<Term>** — <definition>.
