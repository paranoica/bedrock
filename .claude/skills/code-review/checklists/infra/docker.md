# Docker / Dockerfile — infra misconfig checklist

Covers Dockerfiles, `docker run`/Compose, and image build hygiene. The dominant risk is
**container escape → host compromise** and **secret leakage in image layers**. Built on the
spine's misconfig stance. Static helpers: Trivy/Grype (image CVEs), Hadolint (Dockerfile),
Dockle, `docker scout`. Confirmed escape/secret findings → CRITICAL/HIGH.

## Runtime configuration (the escape surface)

- **`--privileged` / `privileged: true`** — disables almost all isolation (host namespaces,
  all capabilities, host devices) → trivial container escape to root on the node. Flag every
  occurrence; legitimate uses (some monitoring agents) are high-risk components to call out.
- **Docker socket mounted in** — `-v /var/run/docker.sock:/var/run/docker.sock` gives the
  container full control of the Docker daemon = root on the host. Treat as critical.
- **`hostPath` / host mounts** — mounting `/`, `/etc`, `/proc`, or host dirs into the container;
  `--pid=host`, `--net=host`, `--ipc=host` share host namespaces → escape/inspection.
- **Added capabilities** — `--cap-add=SYS_ADMIN`/`SYS_PTRACE`/`NET_ADMIN` or not dropping caps;
  `--security-opt seccomp=unconfined` / `apparmor=unconfined` disables syscall filtering. Safe:
  `--cap-drop=ALL` then add only what's needed; keep the default seccomp/AppArmor profiles.
- **Outdated runtime** — note runC version against 2025 escape CVEs (CVE-2025-31133 /
  CVE-2025-52565 class) exploited via crafted mount configs in malicious images/Dockerfiles.

## Dockerfile hygiene

- **Runs as root** — no `USER` directive (default root) → a container escape lands as host root.
  Add a non-root `USER`; prefer minimal/distroless or hardened base images.
- **Secrets baked into layers** — `ENV API_KEY=...`, `ARG` secrets, `COPY .env`, or
  `RUN curl -H "token: ..."` — every layer is persisted and extractable from the image even if
  later "removed". Use BuildKit `--secret` mounts / runtime secrets, never layer-baked secrets.
  Also flag a `.env`/private key copied in due to a missing `.dockerignore`.
- **`latest` / unpinned base** — `FROM node:latest` (or no digest) → non-reproducible, silently
  pulls a changed/compromised base. Pin to a digest (`FROM node:20.11@sha256:...`).
- **`ADD` from a URL / remote tarball** — fetches and auto-extracts remote content (SSRF/tamper);
  prefer `COPY`, or `curl` + checksum verify.
- **`curl | sh` in `RUN`** — unpinned remote code execution at build time.
- **No healthcheck/least-package** — large attack surface; 87% of production images carry
  critical/high CVEs from stale bases (scan with Trivy and treat reachable ones as findings).

## Compose / run specifics

- Secrets via environment (visible in `docker inspect`, process list, logs) instead of Docker
  secrets/mounted files. Ports bound to `0.0.0.0` that should be internal. Containers on the
  default bridge with no network segmentation. `restart: always` masking crash loops.

## What "safe" looks like

- No `--privileged`, no docker.sock mount, no host namespace sharing; `cap-drop=ALL` + minimal
  adds; default seccomp/AppArmor; non-root `USER`.
- Multi-stage build, distroless/pinned-digest base, BuildKit secret mounts, `.dockerignore`
  excluding env/keys/`.git`; image scanned clean (or known-accepted) by Trivy.

Cross-refs: orchestration → `checklists/infra/kubernetes.md`; shell in `RUN` →
`checklists/lang/shell.md`; cloud creds reachable from a container → `checklists/infra/cloud-aws.md`.
