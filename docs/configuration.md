# Configuration and commands

The authoritative validation implementation is `src/tofu_release_kit/config.py`.
Unknown TOML keys, unsupported schema versions, duplicate checks, empty check
lists, invalid identifiers, and unbounded timeouts are rejected.

```toml
schema_version = 1
stack = "orders-api"
environment = "staging"

[policies]
required_tags = ["owner", "environment"]
protected_resources = ["module.storage.aws_dynamodb_table.orders"]
taggable_types = ["aws_dynamodb_table", "aws_lambda_function"]
admin_ports = [22, 3389]

[[verification]]
name = "health"
url_from_output = "health_url"
revision_from_output = "application_revision"
revision_field = "revision"
expected_status = 200
timeout_seconds = 120
request_timeout_seconds = 5
interval_seconds = 2
allow_http = false
```

Protected resources use **exact OpenTofu resource addresses**, including module
paths and instance keys. Patterns are not expanded. Both replacement orders and
forgetting a protected resource are blocked. Exceptions require a separately
reviewed policy/configuration change; there is no bypass flag.

Required tags apply to the configured resource types, including unchanged managed
resources in the saved plan. Default types cover the AWS serverless example and S3.
Provider-level `tags_all` and resource-level `tags` are recognized. Unknown required
tags block approval. This behavior can surface existing violations on adoption.

Verification requires OpenTofu's `output -json` object format. Referenced outputs
must be non-sensitive nonempty strings. `revision_from_output` is optional, but
required by the AWS example to detect a healthy response from an old application.
`revision_field` is a top-level JSON key; arbitrary JSONPath is not supported.
Only 2xx expected status codes are accepted. Redirects are rejected. Body size is
limited to 64 KiB. Per-check deadline: 0.05–600 seconds; request and retry limits:
0.01–30 seconds. There must be 1–20 uniquely named checks.

## Commands

Run `tofu-release-kit COMMAND --help` for complete arguments.

| Command | Input | Output |
| --- | --- | --- |
| inspect | Saved-plan JSON and config | Resource action summary |
| gate | Saved-plan JSON, config, OPA | Allow/deny decision and findings |
| bind | Binary plan and deployment inputs | Binding manifest |
| check-binding | Manifest and current deployment inputs | Valid result or nonzero failure |
| verify | Config and OpenTofu outputs JSON | Required service check results |
| report | Plan, config, apply status, optional verification | Deployment JSON and optional Markdown |

All commands require `--output`. Existing files at that destination are replaced
atomically with private permissions. Keep raw inputs outside version control.
Plan input supports JSON format major version 1; unknown actions and incomplete
or deferred plans fail closed. The maximum JSON file size is 16 MiB.

`--context` on bind/check-binding optionally binds a file describing backend and
account inputs. Use byte-identical canonical JSON for repeatable hashes. It is
mandatory in the supplied AWS workflow. Binding timestamps are real execution
times and are unrelated to synthetic initial repository commit dates.
