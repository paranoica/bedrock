<!--
TEMPLATE — genesis fills this into docs/open-questions.md, parametrized.
Rules:
- First-class "unknown". Do NOT make default assumptions — either ask the user, or record here.
- Use the `decision:` anchor namespace (NOT a separate one): when a question is resolved it
  graduates to decisions.md keeping the SAME slug, so any task that keyed spec_refs on
  decision:<slug> stays valid across the move. Remove the entry here once it graduates.
- A task may list an open decision:<slug> in its spec_refs; spec-analyze then flags that task as
  resting on an unresolved decision (it cannot be declared execution-ready). This is intended —
  the unknown blocks the dependent work instead of floating as a loose note.
-->
# Open questions — <PROJECT NAME>

> Unresolved decisions. Each is anchored with the `decision:` slug it will graduate to.

<!-- @anchor decision:<slug> -->
TODO(decision: <the question, stated precisely> — <options / leaning, or "none stated">; affects <where in the spec/backlog this gates>).
