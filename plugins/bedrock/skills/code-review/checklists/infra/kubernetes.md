# Kubernetes / Helm — infra misconfig checklist

Covers K8s manifests, Helm charts, and cluster config. K8s attacks rose sharply (~282% YoY);
the kill chain is **pod compromise → escape via weak securityContext → node → cluster/cloud
via RBAC**. Built on the spine's misconfig stance. Static helpers: `kube-score`, `kubesec`,
`checkov`/`kube-linter`, Trivy (k8s + image), Polaris; runtime: Falco, Pod Security Admission.
Privileged/RBAC findings → CRITICAL/HIGH.

## Pod securityContext (the escape surface)

Flag a workload (Deployment/StatefulSet/DaemonSet/Pod) missing these:
- `securityContext.privileged: true` → host access, escape (same as Docker `--privileged`).
- `runAsNonRoot: true` + explicit `runAsUser`/`runAsGroup` absent → container runs as root → a
  break-out is host root.
- `allowPrivilegeEscalation: false` not set; `readOnlyRootFilesystem: true` not set.
- `capabilities.drop: ["ALL"]` missing (then add back only e.g. `NET_BIND_SERVICE`);
  dangerous adds (`SYS_ADMIN`, `SYS_PTRACE`, `NET_RAW`).
- `seccompProfile.type: RuntimeDefault` not set (un-filtered syscalls).
- `hostNetwork`/`hostPID`/`hostIPC: true`, or a **`hostPath` volume** (especially `/`,
  `/var/run/docker.sock`, `/proc`) → direct node access / escape.

## RBAC (the lateral-movement surface)

- **`cluster-admin` or wildcard rules bound to a default/namespace-wide service account.** A
  `Role`/`ClusterRole` with `verbs: ["*"]`, `resources: ["*"]`, or `secrets: get/list` granted
  broadly lets a compromised pod read all secrets, create privileged pods, and schedule onto a
  control-plane node → full cluster takeover. Enforce least privilege per service account.
- **Default service account auto-mounted** — pods get the namespace default SA token unless
  `automountServiceAccountToken: false`; a compromised pod uses it against the API. Disable
  automount where the pod doesn't call the API.
- **`escalate`/`bind`/`impersonate` verbs** granted — let a subject grant itself more.

## Secrets & config

- K8s `Secret` objects are **base64, not encrypted** at rest unless etcd encryption is on, and
  visible to anything that can read them — flag secrets in plain manifests/Helm `values.yaml`
  committed to git; use a sealed-secrets/external-secrets/KMS flow. Secrets exposed as env (vs
  mounted files) leak into `kubectl describe`/logs.

## Resource & network

- **No resource `limits`/`requests`** → noisy-neighbor / resource-exhaustion DoS, and no QoS.
- **No `NetworkPolicy`** → flat pod network, any pod can reach any pod/the API/cloud metadata.
- Exposed dashboards/etcd/kubelet read-only port; `LoadBalancer`/`NodePort` exposing internal
  services; the cloud metadata endpoint reachable from pods (SSRF → node IAM creds).

## Helm specifics

- `values.yaml` with hardcoded secrets/passwords; templates that set `privileged`/run-as-root by
  default; `--set` overrides that disable security; unpinned/`latest` image tags in the chart;
  `helm` installed with a broad service account; chart pulled from an unpinned, untrusted repo.

## What "safe" looks like

- Every workload: non-root, no privilege escalation, `cap-drop: ALL`, RuntimeDefault seccomp,
  read-only rootfs, no host namespaces/`hostPath`.
- Least-privilege RBAC per SA, automount disabled where unused, no wildcard verbs/resources.
- Secrets via KMS/external-secrets (not committed), etcd encryption on.
- Resource limits + NetworkPolicy default-deny; Pod Security Admission at `restricted`.

Cross-refs: image/Dockerfile → `checklists/infra/docker.md`; node IAM/metadata →
`checklists/infra/cloud-aws.md`; IaC that provisions the cluster → `checklists/infra/terraform.md`.
