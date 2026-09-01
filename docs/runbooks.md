# Operating runbooks

## Policy blocked

Read the rule ID and resource address. Fix missing tags or unintended public
ingress in source. For intended protected-resource replacement, assess data backup,
restoration, application interruption, and ownership before reviewing an explicit
exception. A new plan and approval are required after any configuration change.

## Plan binding rejected

Compare commit, environment, OpenTofu version, backend context, configuration, and
provider lockfile. Never edit a binding to make it pass. Expired plans need a fresh
plan and review. Verify that no other controller is writing the state.

## Apply failed

An apply can change some resources before failing. Preserve state and inspect the
cloud with restricted credentials. Resolve the provider/API issue, refresh through
a new plan, and review the resulting delta. Do not blindly retry the old saved plan
or restore an old state file to undo resource changes.

## Apply succeeded, service failed

Use the fixed reason (`status_mismatch`, `revision_mismatch`, `connection_error`,
`request_timeout`, or invalid response) to guide investigation. Check application
logs and dependency permissions privately. An old revision indicates stale routing
or an incomplete rollout. Re-deploy a known-good application revision through a
newly reviewed plan, or roll forward with a fix. Inspect health again before closing.

## State lock conflict

Find the owning run and determine whether it is still active. Let active work finish.
Only use force-unlock after establishing that the owner has terminated and recording
that decision. A lock protects state concurrency; it is not a cross-service transaction.

## Drift

Run a normal refreshed `tofu plan -detailed-exitcode`: 0 means no changes, 2 means
changes, 1 means error. Review drift and configuration changes together. An error
must not be reported as clean. Choose whether to encode an intentional external
change in source or restore the declared configuration. This toolkit does not
discover arbitrary resources that were never managed in the selected state.

## Recovery exercise

Use `examples/recovery-local` to rehearse local state backup, a moved block, and
an encryption-key failure. Record expected/observed outcomes. For real remote state,
restore only after stopping writers, preserving the current state, confirming the
resource inventory, and checking lineage/serial. Keep old decryption keys available
through the retention period of encrypted backups.
