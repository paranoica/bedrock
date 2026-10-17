# Terraform / IaC — infra misconfig checklist

Covers Terraform/OpenTofu (HCL), and the same patterns in CloudFormation/Pulumi/Ansible. The
defining property: **a misconfig in code deploys automatically to production, with a large
blast radius** (one `apply` can touch hundreds of resources). Misconfiguration drives ~63% of
cloud incidents. Built on the spine's misconfig stance. Static helpers: `checkov`, `tfsec`/Trivy,
`terrascan`, KICS — run them and cross-reference. The cloud-resource semantics live in
`checklists/infra/cloud-aws.md`; this file is the IaC-layer concerns.

## Secrets & state (IaC-specific, often missed)

- **Hardcoded credentials/secrets in HCL** — `access_key`/`secret_key` in a `provider` block,
  DB passwords, API keys, private keys as string literals or in `*.tfvars` committed to git.
  Use a secrets manager (Vault / AWS Secrets Manager) referenced at runtime, or provider env/
  role auth — never literals.
- **State file = plaintext secrets.** `terraform.tfstate` stores generated passwords, RDS
  connection details, SSH keys, and any `sensitive` value **in cleartext**. A local state file
  in git, or a remote backend bucket that's unencrypted/world-readable, leaks the whole
  infrastructure's secrets. Require: remote backend (S3/GCS) with encryption + locking +
  restrictive bucket policy; state never committed; `sensitive = true` on outputs (and know it
  still sits in state).
- **Plan/diagnostic leakage** — secrets printed in `terraform plan` output or CI logs,
  especially on failed applies. Don't echo plan output with secrets into CI artifacts.

## Resource misconfigs to flag in the code

- **Public object storage** — `aws_s3_bucket` with `acl = "public-read"`/`"public-read-write"`,
  missing `aws_s3_bucket_public_access_block` (all four `block_*`/`restrict_*` = true), missing
  default encryption. (CloudFormation: missing `PublicAccessBlockConfiguration`.)
- **Open ingress** — `aws_security_group` ingress `cidr_blocks = ["0.0.0.0/0"]` (or `::/0`) on
  22/3389/database ports or `from_port = 0 to_port = 65535`. Restrict to known CIDRs/SGs.
- **IAM wildcards** — a policy with `Action = "*"` and/or `Resource = "*"`, `Effect = "Allow"`;
  `AdministratorAccess` attached broadly; `iam:PassRole`/`sts:AssumeRole` too broad; trust
  policies with `Principal = "*"`. Least privilege, scoped resources.
- **No encryption at rest** — RDS/EBS/S3/SNS/SQS without `kms_key_id`/`encrypted = true`;
  databases with `publicly_accessible = true`; `storage_encrypted` unset.
- **Logging/audit off** — no CloudTrail (multi-region, log-file validation), no flow logs,
  no GuardDuty; resources allowing unencrypted transport.

## IaC-pipeline & module supply chain

- Modules sourced from an **unpinned** registry/git ref (`?ref=main`) → mutable third-party
  code provisioning your infra; pin to a version/commit. Provider versions unpinned.
- A CI pipeline running `terraform apply` with broad cloud credentials and no plan-review gate
  (cross-ref `checklists/infra/ci-cd.md`) — supply-chain attacks on IaC pipelines rose sharply.

## What "safe" looks like

- No literal secrets anywhere; remote encrypted+locked+restricted state backend; secrets via a
  manager.
- S3 private + public-access-block + encryption; SGs scoped to specific CIDRs/SGs; IAM scoped to
  specific actions/resources; encryption-at-rest + TLS on every data store.
- CloudTrail/GuardDuty/flow-logs on; modules and providers pinned; `apply` gated behind a
  reviewed plan with least-privilege CI creds.
- `checkov`/`tfsec` clean (or each finding triaged with a documented exception).
