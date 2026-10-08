# Contributing

Use Python 3.11+, OPA 1.21.1, and OpenTofu 1.13.1. The CLI has no runtime Python dependencies.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/install_tools.py --tofu
export PATH="$PWD/.tools:$PATH"
make check
```

The installer supports Linux x86_64. On macOS, install the matching official
OPA/OpenTofu releases for your architecture and verify their published checksums.
Windows contributors can use WSL2. The container currently targets Linux x86_64.

Fork pull requests run on hosted runners without cloud secrets. Never request
cloud credentials to reproduce the standard test suite. A live-cloud test must
be clearly marked, optional, scoped to a disposable sandbox, and include cleanup.

Include the failure case when fixing a bug. Policy changes need both a permitted
fixture and a prohibited/unknown-value fixture. Parser changes need fixtures for
the supported plan format. Keep real plan/state files and customer resource names
out of test fixtures. Use synthetic values and describe the scenario.

Start a focused branch from `dev`; open a PR into `dev`. Keep commits meaningful.
Use actual dates for subsequent maintenance. Release changes go from `dev` to
`main` after checks pass. Maintainers can squash those release PRs.

The version in pyproject.toml and src/tofu_release_kit/__init__.py must agree.
A matching `vX.Y.Z` tag runs release validation and creates a draft GitHub release
with distributions, checksums, and build provenance. Review it before publication.

Good first contributions include synthetic policy fixtures, improved recovery
instructions verified in an isolated lab, and focused documentation corrections.
