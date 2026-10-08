# Tofu Release Kit

[![CI](https://github.com/rclevenger-hm/tofu-release-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/rclevenger-hm/tofu-release-kit/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Review infrastructure changes, enforce policy, and verify the deployed service.**

Tofu Release Kit gives platform teams a small CLI, a reusable GitHub Action, and
a reference deployment workflow connecting an OpenTofu plan to service readiness.
It records what changed, whether policy allowed it, whether apply succeeded, and
whether the expected application revision became healthy.

**Status: v0.1 alpha implementation.** The cloud-free demo works without cloud
credentials. The AWS example requires operator setup; no live deployment is implied
by mocked tests. Azure/ECS and a validated Spacelift adapter are tracked follow-ups.

## Try it without a cloud account

Python 3.11+ and OPA 1.21.1 are required. Linux x86_64 quickstart:

```sh
git clone https://github.com/rclevenger-hm/tofu-release-kit.git
cd tofu-release-kit
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/install_tools.py
export PATH="$PWD/.tools:$PATH"
make demo
```

On macOS, install the matching official OPA binary and verify its checksum. See
[contributing](CONTRIBUTING.md) for development setup and Windows/WSL guidance.

The demo starts a temporary localhost service and uses synthetic plans. It exercises
three outcomes and writes labeled simulation reports into `.artifacts/demo/`:

| Scenario | Expected result |
| --- | --- |
| Healthy service with expected revision | `verified` |
| Attempted deletion of a protected table | `blocked` |
| HTTP 200 from an old application revision | `verification_failed` |

Every scenario exits successfully only when its expected outcome is observed.
The underlying CLI exits nonzero on policy rejection or deployment failure.

## Use it with your infrastructure

Generate a saved plan and JSON representation in a private directory, then run:

```sh
tofu-release-kit report \
  --plan /private/plan.json \
  --config release-kit.toml \
  --output /private/review.json \
  --markdown /private/review.md
```

Use `verify` after a successful apply to check the service and expected revision.
Pass its result to `report --apply-status succeeded --verification ...` to produce
the final deployment record. Plans, state, and outputs can contain secrets: keep
them out of Git and public artifacts. Reports omit attribute values, but resource
addresses can still be sensitive.

The reusable action lives at `.github/actions/review`. Pin the repository reference
to an audited full commit SHA when consuming it from another repository. It expects
a private runner-local plan file and Linux x86_64 with Python 3.11+ available.

## Capabilities

- **Plan review:** distinguish additions, updates, both replacement orders, deletes,
  reads, and forgotten resources; reject malformed or incomplete plans.
- **Policy:** protect exact resource addresses, require ownership tags, and block
  public administrative ingress for supported AWS security-group resource types.
- **Plan binding:** detect changed commits, environments, tool versions, dependency
  locks, configuration, backend context, and expired reviewed plans.
- **Service checks:** validate status and application revision with hard process
  deadlines, bounded responses, verified TLS, and explicit failure reasons.
- **Operational reporting:** separate policy rejection, partial apply failure,
  missing verification, failed verification, and verified deployment.
- **AWS reference delivery:** OIDC roles, state locking, an approval environment,
  encrypted plan transfer, deterministic Lambda packaging, and dependency readiness.

The core CLI has no runtime Python dependencies. OPA supplies policy evaluation.
OpenTofu and the CI platform retain ownership of provisioning, state, and approval.

## Learn and operate

| Guide | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Responsibilities, trust boundaries, and outcomes |
| [Configuration](docs/configuration.md) | Schema and CLI contract |
| [AWS sandbox setup](docs/aws-setup.md) | Credentials, backend, approval, costs, and teardown |
| [Runbooks](docs/runbooks.md) | Policy rejection, stale plans, failed applies, health failures, drift |
| [Migration](docs/migration.md) | Version-aware Terraform-to-OpenTofu exercise |
| [Local recovery lab](examples/recovery-local/README.md) | State, moved resources, and missing encryption keys |
| [Spacelift recipe](integrations/spacelift/README.md) | Integration boundaries and validation still required |
| [Roadmap](docs/roadmap.md) | Cloud portability and release milestones |
| [Security](SECURITY.md) | Limits and secure adoption |

## Development and releases

`make check` runs Python tests, Rego tests, and all local demo scenarios. CI also
validates OpenTofu with mocked AWS resources, checks installable distributions,
and smoke-tests the container. The manual AWS workflow is separate from PR CI.
Matching version tags build distributions and create a draft release for review.

Development proceeds on `dev`, with reviewed release changes into `main`.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [RELEASE_NOTES.md](RELEASE_NOTES.md).

License: [Apache-2.0](LICENSE). Initial import timestamps are synthetic;
[HISTORY.md](HISTORY.md) explains their provenance and actual development period.
