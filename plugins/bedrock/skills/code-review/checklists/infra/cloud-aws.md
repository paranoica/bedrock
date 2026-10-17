# Cloud / AWS — infra security checklist

Covers AWS resource configuration and app-level cloud usage (SDK calls, IAM, S3, metadata),
with patterns that generalize to GCP/Azure. Applies whether resources are clicked, scripted,
or provisioned via IaC (`checklists/infra/terraform.md` covers the HCL layer). Misconfig drives
~63% of cloud incidents; IAM issues ~47% of breaches. Built on the spine's misconfig +
SSRF/SSRF-to-metadata stance.

## The metadata SSRF chain (highest-value app finding)

A server-side request to a tainted URL that can reach **`http://169.254.169.254/`** (the
instance metadata endpoint) yields the instance's IAM role credentials → cloud account access.
This is the S8 sink from the spine, with cloud-specific weight. Flag any outbound fetch of a
user-controlled URL on an EC2/ECS/EKS host. Require: **IMDSv2** (token-required, hop-limit 1)
enforced, plus an SSRF allowlist that blocks link-local/private ranges and re-checks after
redirects/DNS resolution.

## IAM (the lateral-movement surface)

- **Wildcard policies** — `Action: "*"` / `Resource: "*"` / `AdministratorAccess` attached to
  app roles or users; over-broad `iam:PassRole`, `sts:AssumeRole`, `s3:*`, `kms:*`.
- **Long-lived access keys** in code/env/CI instead of role assumption / OIDC; keys never
  rotated; root account access keys existing at all.
- **Confused-deputy / trust gaps** — role trust policy with `Principal: "*"` or a wildcard
  external account; missing `aws:SourceArn`/`ExternalId` conditions on cross-account/3rd-party
  trust.
- **Privilege-escalation IAM paths** — a role that can `iam:CreatePolicyVersion`,
  `iam:AttachUserPolicy`, `iam:PutRolePolicy`, or `lambda:UpdateFunctionCode` can escalate to
  admin; flag these grants.

## Data exposure

- **Public S3** — bucket/object ACL public, no account/bucket Public Access Block, policy with
  `Principal: "*"`; pre-signed URLs with very long expiry or generated from user input;
  unencrypted buckets; no TLS-only bucket policy.
- **Public data stores** — RDS/Redshift/Elasticsearch/DocumentDB `publicly_accessible`, open SG,
  no encryption at rest/in transit; snapshots shared publicly.
- **Secrets** — credentials in Lambda env vars (visible in console/logs) instead of Secrets
  Manager/Parameter Store (SecureString); secrets in CloudFormation/Terraform outputs; secrets
  in container env (cross-ref docker/k8s).

## Serverless / app-level

- **Lambda** — over-broad execution role; function URL/`AuthType: NONE` exposed; event-source
  (S3/SQS/API GW) input treated as trusted (it's tainted — apply the spine); `eval`-style
  dynamic execution.
- **API Gateway** — no authorizer / `authorizationType: NONE` on a sensitive route; missing
  throttling (cost + DoS, cross-ref `checklists/finops.md`); CORS `*` with credentials.
- **SQS/SNS/EventBridge** — policies allowing `Principal: "*"` to publish/subscribe.

## Logging & guardrails

- CloudTrail off / single-region / no log-file validation; no GuardDuty / Security Hub /
  Config; VPC flow logs off; CloudWatch log groups unencrypted or never expiring (cost).

## What "safe" looks like

- IMDSv2 enforced + SSRF allowlist; no app fetch of user URLs without host allowlisting.
- IAM least-privilege, scoped actions+resources, no wildcards on app roles; role assumption/
  OIDC over long-lived keys; trust conditions on cross-account.
- S3 private + Public Access Block + encryption + TLS-only; data stores private + encrypted;
  secrets in Secrets Manager/SSM SecureString.
- CloudTrail (multi-region, validated) + GuardDuty + Config on; least-privilege Lambda roles;
  authorizers + throttling on API GW.

Cross-refs: provisioning → `checklists/infra/terraform.md`; SSRF mechanics → `checklists/taint-spine.md`
(S8); pod-to-metadata → `checklists/infra/kubernetes.md`; cost-blast → `checklists/finops.md`.
