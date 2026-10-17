# Export search results to CSV

Risk / priority: R2 P2 — a new output format, no stored data changes
Done when: export works well
Stands on: —

## Assumptions
- Results are written as `document,chunk,score` per line.

## Files
- docsearch/export.py (new)
- docsearch/cli.py
- docsearch/index.py (switch the index to CSV as well, for consistency)

## Tests
- test_export_writes_rows — three hits give three lines

## Tasks
| id | task | files | test | who (model) | estimate |
|---|---|---|---|---|---|
| T1 | export module and CLI flag | export.py, cli.py, index.py | test_export_writes_rows | agent (sonnet) | 30 |

## Estimate
30 min

## Out of scope
- Excel files
