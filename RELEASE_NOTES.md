# 0.1.0 — Review and verify

Initial alpha implementation:

- Strict TOML configuration and saved-plan JSON validation.
- OPA/Rego policy checks for protected resources, required tags, and public administrative ingress.
- Saved-plan binding to commit, environment, dependency lockfile, toolkit configuration, and optional backend context.
- Revision-aware HTTP readiness checks with bounded processes and retries.
- Separate policy, apply, and service-verification outcomes in Markdown and JSON reports.
- Cloud-free demonstrations and an AWS reference deployment with encrypted plan transfer.
- Package, container, policy, OpenTofu, and workflow validation.

Cloud resources are provisioned only through an explicitly configured manual workflow.
Live AWS deployment and Spacelift execution require operator validation in their own sandbox.
Azure/ECS modules and optional language-model explanations are planned follow-up work.

This release is suitable for evaluation. Reports are operational records, not signed
compliance attestations. Read SECURITY.md before connecting cloud credentials.
