# Evals

The skill is software; this directory tests it. It has two layers.

## 1. Deterministic regressions — `./run_evals.sh`

No model calls. Guards the concrete bugs v1 shipped:

- **Lockfile parser coverage** — pnpm v9 and yarn Berry must parse to non-empty.
  (v1 silently returned `[]` for both, producing a false "no vulnerable deps".)
- **Hallucination cuts** — `verify_findings.py` must cut a fabricated file, a
  fabricated quote, and a fabricated CVE.
- **No over-cutting** — a real finding on the vuln fixture must survive.

Run it in CI on every change to the skill:

```bash
./evals/run_evals.sh   # exits non-zero if any regression fails
```

## 2. Review-quality scoring — `score.py`

Measures an actual review run against labeled fixtures. Because this needs the skill
to actually review the code, it's a two-step:

1. Point the skill at `evals/fixtures/` and have it produce a `findings.json`
   (the Step 5c artifact).
2. Score it:

```bash
python3 evals/score.py <candidate_findings.json> evals/expected.json evals
```

Metrics:
- **recall** — fraction of `must_catch` issues found (target: 1.0)
- **false_positives** — findings on `must_not_flag` files (target: 0)
- **hallucinations** — findings that fail grounding via `verify_findings.py` (target: 0)

A run passes only at recall 1.0, 0 FP, 0 hallucinations.

## The labeled corpus (`fixtures/` + `expected.json`)

24 vuln/safe pairs. Each pair is aimed at the **signature footgun the matching
module documents**, not a generic re-test of the taint-spine — the point is to
exercise the language/infra-specific sink and, via the safe twin, prove the review
does *not* fire on the correct idiom (the precision half of F1).

Languages (one canonical class each, per `checklists/lang/*` + the deep modules):

| Module | vuln class | safe twin |
|---|---|---|
| Python | f-string SQLi · shell cmdi · path traversal | parameterized · arg-vector · realpath-confined |
| C | `strcpy` overflow | `snprintf` bounded |
| JS/TS | prototype pollution (`__proto__` via merge) | proto-key block + null-proto |
| Go | `exec.Command("sh","-c", …)` (G204) | fixed binary + arg slice |
| Java | `ObjectInputStream.readObject` (gadget RCE) | typed JSON bind |
| C++ | iterator/reference invalidation (UAF) | reserve + copy, no held ref |
| C# | `BinaryFormatter.Deserialize` | `System.Text.Json` to a DTO |
| PHP | `unserialize($_GET)` object injection | `json_decode` |
| Rust | `unsafe { from_raw_parts(p, attacker_len) }` | bounds-checked safe slice |
| Shell | `eval "$user"` + word-splitting | `set -euo pipefail` + quoted + `--` |
| Kotlin | string-template SQL (`"… = $id"`) | prepared statement |
| Dart | `badCertificateCallback => true` | default system trust |
| Swift | trust-all `URLSession` delegate | `.performDefaultHandling` |

Infra (canonical misconfig each, per `checklists/infra/*`):

| Module | vuln class | safe twin |
|---|---|---|
| Docker | root + secret baked in a layer + `:latest` | non-root `USER`, pinned base, runtime secret |
| Kubernetes | `securityContext.privileged: true` | drop-ALL caps, runAsNonRoot, RO rootfs |
| Terraform | SG ingress `0.0.0.0/0` on 22 | CIDR var-restricted |
| CI/CD | `pull_request_target` + checkout of PR head | `pull_request`, read-only token |
| Nginx | `alias` off-by-slash traversal | matched trailing slashes |
| AWS IAM | `Action:"*" Resource:"*"` | scoped action + resource ARN |
| Redis | `bind 0.0.0.0` + `protected-mode no`, no auth | localhost bind + `requirepass` |
| Postgres | `pg_hba` `trust` from `0.0.0.0/0` | `hostssl` + `scram-sha-256` |
| GraphQL | prod `introspection: true`, no depth cap | env-gated + `depthLimit` + complexity rule |

## Extending the corpus

Don't hand-edit three files in sync — use the builder. Add a dict to
`build_fixtures.py` (vuln + safe content, the unique `sink` line, category,
severity, tag); it writes both files and appends self-consistent entries to
`expected.json` and `golden_candidate.json` (line numbers and the golden quote are
computed from the file, so they never drift). Then run `./run_evals.sh` — test 7
re-scores the golden candidate and fails on any recall/precision regression.

Schema, if editing by hand anyway:
- `must_catch`: `{file, category, min_severity, near_line, tag}` — a real issue.
- `must_not_flag`: `{file, reason}` — safe code that must not produce a finding.
- the golden quote must be the **verbatim** sink line at the claimed `lines`, or
  `verify_findings.py` cuts it and the self-test goes red.

Keep each fixture minimal and single-purpose. This is the regression suite that lets
you change prompts/checklists without silently losing recall or gaining false
positives — the thing v1's "46/46, 0 FP" README claim asserted but never measured.
