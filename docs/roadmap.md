# Roadmap

## 0.1: Review and verify — implemented

- Python CLI, strict config, and plan-format validation.
- Tested Rego policies and a reusable GitHub review action.
- Revision-aware verification and limited Markdown/JSON reports.
- Plan binding and encrypted transfer between deployment jobs.
- Cloud-free demo and AWS serverless reference workflow.
- Local recovery/encryption lab and client-facing runbooks.
- CI and draft release workflow.

Live cloud execution still requires a separately configured sandbox and recorded
evidence. A green mocked test is not proof of a successful AWS deployment.

## 0.2: Portable reference workloads

Tracking: [live AWS validation #7](https://github.com/rclevenger-hm/tofu-release-kit/issues/7),
[AWS/Azure containers #8](https://github.com/rclevenger-hm/tofu-release-kit/issues/8),
[Spacelift integration #9](https://github.com/rclevenger-hm/tofu-release-kit/issues/9).

1. Deploy one containerized service through AWS ECS and Azure Container Apps.
   Share input/output contracts while retaining explicit cloud-specific modules.
   Add identity, networking, logs, scoped permissions, and a teardown procedure.
2. Validate a Spacelift adapter against the same policy and outcome fixtures.
3. Package backend/OIDC bootstrap modules after validating account boundary choices.
4. Add AWS live integration evidence and a reviewed least-privilege deploy-role policy.

## 0.3: Recovery and change operations

Tracking: [drift and recovery matrix #10](https://github.com/rclevenger-hm/tofu-release-kit/issues/10).

1. Add scheduled drift reporting with correct 0/1/2 exit handling and no automatic
   reconciliation. Clearly scope it to resources managed by the selected state.
2. Validate a Terraform-to-OpenTofu migration matrix for explicit supported versions.
3. Add remote encrypted-state recovery drills and tested key-rotation guidance.

## 1.0: Stable adoption

Freeze the configuration/report schemas, publish compatibility and upgrade matrices,
run consumer-repository integration tests, and document supported workflows. Use
actual release dates and distinguish supported features from examples.

## Optional later extension

An opt-in report explainer may consume only an allowlisted summary and cite resource
addresses. Evaluate explanations on known cases. Keep secrets and raw plans out of
requests; retain deterministic policy and human approval. Core use must remain
possible without a model API, paid service, or cloud account.
