# Supply-chain checklist

Read when a diff adds or bumps dependencies, or touches `package.json` scripts,
lockfiles, or CI. OSV (Step 3) catches *known* CVEs in deps; this catches the rest:
malicious or risky packages, install-time code execution, and lockfile tampering.

## New / changed dependencies
- **Typosquatting & confusion.** A new dep whose name is one edit away from a popular
  package (`reqeusts`, `lodahs`, `python-dateutil` vs a look-alike), or a public name
  that shadows an internal/private package (dependency confusion). Verify the package is
  the real, intended one.
- **Brand-new or low-trust package** pulled in for a trivial task — weigh against writing
  a few lines instead of adding an unvetted dependency and its transitive tree.
- **Suspicious version jump or pin to an odd version** (e.g. pinning to a just-published
  `0.0.x` of a previously-stable package) — possible account compromise / malicious release.
- **Git/URL/tarball dependencies** instead of registry (`"dep": "git+https://…"`,
  `file:`, arbitrary URL) — bypass registry controls; scrutinize the source.
- **License regressions:** a new dep under a copyleft (GPL/AGPL) or non-OSI license in a
  proprietary codebase. Flag for legal, not as a security bug.

## Install-time code execution (npm)
- **`package.json` lifecycle scripts**: `preinstall`, `install`, `postinstall`,
  `prepare`. Arbitrary code that runs on `npm install` is a prime malware vector. A new
  or changed `postinstall` that curls a script, runs a binary, or touches the network/FS
  is a serious finding.
- **`scripts` that pipe to a shell from the network** (`curl … | sh`, `wget … | bash`)
  anywhere in build/CI.
- New **`bin` entries** or **`gypfile`/native build** steps added by a dep update.

## Lockfile integrity
- **Manifest ↔ lockfile drift:** a change to `package.json` / `pyproject.toml` /
  `requirements.txt` with no corresponding lockfile update (or vice-versa). Means the
  reviewed versions aren't what installs.
- **Lockfile edited by hand** / integrity hashes changed without a version change —
  possible tampering. Resolved URLs pointing somewhere other than the official registry.
- **Unpinned production deps** (ranges like `^`, `*`, `latest` in places that should be
  locked) — non-reproducible builds, surprise upgrades.

## Maintenance health (not a CVE, but real risk)
- **Dead / unmaintained dep**: last release years old, archived repo, single maintainer
  with no activity — bus factor and un-patchable future CVEs.
- **Deprecated package** still in use where a maintained replacement exists.
- **Sudden maintainer change** on a sensitive low-level package.

## CI / workflow supply-chain
- **GitHub Actions pinned to a mutable tag** (`@v4`, `@main`) instead of a commit SHA —
  a compromised action can run with repo secrets.
- New workflow with access to secrets triggered by untrusted events
  (`pull_request_target` + checkout of PR code).

## What NOT to flag
- Routine patch/minor bumps of well-known deps with a matching lockfile update.
- `postinstall` that's a normal, well-understood build step for a known package
  (e.g. native module compile) — note it only if it's new *and* opaque.
- Dev-only dependencies for license concerns in most contexts (confirm the policy).
- Range specifiers in libraries meant to be consumed by others (where pinning is wrong).
