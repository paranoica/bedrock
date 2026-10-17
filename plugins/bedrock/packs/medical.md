# Pack: Medical data

## Rules
- Only synthetic data in the repository, fixtures, the knowledge base and logs.
- Log redaction is verified by a test; no patient identifier reaches a log line.
- The 18 HIPAA identifiers are the coverage list for redaction and for PHI checks.
- Presidio runs as the PHI check when fixtures, test data or logging config change (D052).
  It is a detector, not a certification. It is installed on the owner's word: until then the
  report says the PHI check did not run.
- Meaning is decided by the strongest models at the highest effort; small models never
  decide what a clinical text means (D011).

## Clinical invariants
Negation, family history, temporality (past or current), uncertainty ("possible", "rule
out"), units and reference ranges, doses.

## Critical zones to consider
Clinical extraction and its meaning, document chunking and ingestion, patient data storage,
access control.

## Reviewer checklist
- Every extracted fact traces to its source span.
- Units are converted explicitly; a missing unit is an error, not a default.
- Access to patient data is logged and limited to the role that needs it.

## Test checklist
Metamorphic tests (the `hunt` skill):
- a paraphrase keeps the extracted facts;
- an added negation never yields a positive fact;
- a relative's condition is never the patient's;
- document order does not change the facts;
- a fact split across a chunk boundary is still found.
