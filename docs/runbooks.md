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

An interrupted create-before-destroy replacement can leave a deposed (old) object
alongside the current object at the same resource address. Review each object in
the new plan; reports label old objects with their deposed key. A cleanup deletion
at a protected address still requires a separately reviewed exception. Do not
remove the old object from state just to bypass policy or the recovery review.

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

Generate a fresh plan from a trusted, initialized configuration and the intended
backend/workspace. A normal refreshed plan includes proposed configuration changes;
use `-refresh-only` when you only want to inspect changes observed since the stored
state. Do not disable refresh or use resource targeting for a full-state check.

This shell example keeps plans and diagnostics in a new private directory, handles
all three OpenTofu codes, and never applies or updates state:

```sh
umask 077
evidence=$(mktemp -d)
plan_code=0
tofu plan -refresh-only -input=false -detailed-exitcode \
  -out="$evidence/plan.bin" >"$evidence/plan.log" 2>&1 || plan_code=$?
case "$plan_code" in
  0|2)
    tofu show -json "$evidence/plan.bin" >"$evidence/plan.json" || exit 2
    tofu-release-kit drift --config release-kit.toml \
      --plan-exit-code "$plan_code" --plan "$evidence/plan.json" \
      --output "$evidence/drift.json"
    ;;
  1)
    tofu-release-kit drift --config release-kit.toml --plan-exit-code 1 \
      --output "$evidence/drift.json"
    ;;
  *) exit 2 ;;
esac
```

The report command is offline: it does not invoke OpenTofu, providers, OPA, or apply.
Planning itself can invoke providers/data sources, needs authorized read access,
and may acquire a backend lock. Review the trusted configuration before running it.
Inspect failures through the private log; never upload raw plans, state, or logs.
Remove the temporary evidence after your retention/review requirements are met.

`drift_detected` means the supplied plan observed changes to managed resources.
`changes_detected` means OpenTofu reported changes but no managed-resource drift was
identified, such as output or configuration changes. `plan_error` never means clean.
See [command and exit-code details](configuration.md#drift-reports).

The supplied JSON cannot prove refresh occurred, authenticate the exit code, or
verify backend/workspace identity. Results describe one snapshot of the selected
state, not ongoing cloud health or resources never managed there. The local test
covers real OpenTofu clean/output-change/error plans without cloud resources;
managed drift and recovery-object cases use synthetic fixtures. Scheduling and
live drift, remote-state recovery, and migration-version validation remain in
[issue #10](https://github.com/rclevenger-hm/tofu-release-kit/issues/10).

After review, choose whether to encode an intentional external change in source
or restore the declared configuration through a separately approved delivery run.

## Recovery exercise

Use `examples/recovery-local` to rehearse local state backup, a moved block, and
an encryption-key failure. Record expected/observed outcomes. For real remote state,
restore only after stopping writers, preserving the current state, confirming the
resource inventory, and checking lineage/serial. Keep old decryption keys available
through the retention period of encrypted backups.
