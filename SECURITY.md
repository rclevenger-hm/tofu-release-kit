# Security and trust boundaries

Use GitHub's private vulnerability reporting if enabled, or contact the maintainer
privately before disclosing exploitable details. Do not attach raw plans, state,
credentials, or customer information to a public issue.

The first release is an evaluation toolkit, not a complete cloud security scanner.
The public-admin rule covers AWS security group inline ingress, standalone security
group ingress rules, and VPC security group ingress rules. It does not analyze IAM,
NACLs, public load balancers, Azure networking, or reachability through other layers.
The tags rule applies only to configured resource types. Policies do not certify
compliance or guarantee safety.

OpenTofu providers and configuration can execute code during planning. Cloud plans
must run only from trusted reviewed commits. Public fork PRs receive no cloud
credentials, write tokens, or persistent self-hosted runner access. Do not change
the example workflow to check out untrusted PR code using pull_request_target.

Raw plan JSON and state can expose secrets even when terminal output is redacted.
The toolkit emits resource addresses, action types, rule identifiers, and fixed
verification outcomes. Addresses and policy tag names can still be confidential:
use private repositories/reports where appropriate. Private intermediate logs and
plan JSON are never uploaded by the reference workflow.

Saved plans and their binding manifests travel between trusted jobs in a GnuPG
AES-256 encrypted, integrity-protected payload. Store a random 32+ character
TRK_PLAN_KEY as a repository secret. Protect its access and rotate it after suspected
exposure. The key must be available to both jobs. Artifacts expire after one day.
Encryption does not authenticate the identity of whoever holds that key.

The binding is a consistency check, not a digital signature. Its integrity depends
on the trusted workflow, encrypted artifact, repository permissions, and CI approval
controls. It cannot prevent an authorized runner from replacing both manifest and
plan. OpenTofu itself rejects saved plans made stale by changed state. External
cloud changes not represented in state remain a native saved-plan limitation;
keep the approval window short and re-plan after suspected drift.

Verification URLs come from trusted configuration and outputs. The verifier can
reach private services reachable by its runner; treat it as a network-capable
workload. It verifies TLS, rejects redirects, URL credentials, query strings, and
fragments, and disables inherited HTTP proxies. Plain HTTP requires explicit opt-in.
Authentication headers and arbitrary shell checks are deliberately outside v0.1.
Response bodies and URLs are not included in reports.

Configure a protected `sandbox` GitHub Environment with required reviewers and
restricted branches before running the AWS example. Environment names alone do
not enforce approval. Scope OIDC trust to the repository and branch/environment;
use separate plan and apply roles. Keep state in a versioned encrypted bucket with
locking and scoped KMS permissions. The example never auto-destroys infrastructure.
