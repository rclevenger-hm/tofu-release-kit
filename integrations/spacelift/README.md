# Spacelift adapter recipe

Status: integration recipe; not yet validated in a live Spacelift account. The CLI
and policy bundle are tested independently. Use a sandbox stack to validate the
hook contract for your Spacelift worker and OpenTofu versions before adoption.

Let Spacelift own OpenTofu execution, state, approval, and drift scheduling. Use the
toolkit for shared review and verification. Do not run the GitHub apply workflow
against the same state.

1. Install a pinned toolkit revision and the tested OPA release in your private
   worker image. Keep policy files from that same release.
2. In an after-plan integration, obtain a saved-plan JSON file using the documented
   plan artifact location for your worker. Pass it to the CLI `report` command with
   the stack's release-kit.toml. Preserve exit code 1 or 2 as a failed run.
3. Configure Spacelift's native approval policy for apply authorization. Adapt its
   plan-policy input through a documented mapping if integrating the Rego rules
   directly; Spacelift's input envelope is not identical to the CLI envelope.
4. After a successful apply, write `tofu output -json` into a private temporary file
   and run `verify`. Preserve any nonzero exit status and publish only limited reports.
5. Capture the same stack, source revision, and run identity in your run record.

Example hook body once the plan location has been resolved by the worker:

```sh
umask 077
tofu-release-kit report --plan "$PRIVATE_PLAN_JSON" --config release-kit.toml \
  --output "$PRIVATE_REPORT_DIR/review.json" --markdown "$PRIVATE_REPORT_DIR/review.md"
```

The adapter deliberately does not guess vendor-generated filenames or claim a
tested turnkey stack. A follow-up milestone will validate hook execution, plan
policy mapping, and identical failure outcomes in both platforms.

References:
- https://docs.spacelift.io/concepts/run
- https://docs.spacelift.io/concepts/policy
- https://docs.spacelift.io/concepts/stack/drift-detection
