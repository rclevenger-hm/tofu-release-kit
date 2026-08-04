# Local recovery lab

No cloud account or provider download is needed. Work in an isolated copy outside
the repository. The resource stores a value in local state; it creates no real
service. Use OpenTofu 1.13.1 for the encryption exercise.

```sh
mkdir -p /tmp/trk-recovery
cp examples/recovery-local/main.tf /tmp/trk-recovery/
tofu -chdir=/tmp/trk-recovery init
tofu -chdir=/tmp/trk-recovery apply -auto-approve
tofu -chdir=/tmp/trk-recovery plan -detailed-exitcode
```

The final command should exit 0. Back up `terraform.tfstate` privately, record the
resource ID, change `revision` using `-var=revision=second`, and apply again. Observe
that a state backup is an inventory snapshot, not an undo operation.

## Resource refactor

In your isolated copy rename `terraform_data.release` to `terraform_data.deployment`
and update the output reference. Add this to the configuration:

```hcl
moved {
  from = terraform_data.release
  to   = terraform_data.deployment
}
```

Plan and verify that the resource is moved without replacement. Apply and compare
its ID. Retain moved blocks while downstream users could still have old state.

## Encryption and missing-key exercise

Start a **new empty directory** with copies of main.tf and encryption.tf.example,
renaming the latter to encryption.tf. Set TF_VAR_state_passphrase securely in your
shell, initialize, and apply. Do not commit or print the passphrase or state.

Unset the passphrase and run `tofu plan -input=false`: it must fail. Restore the
correct passphrase and obtain a no-change plan. A wrong key must also fail. Keep
the working key available until the lab is destroyed. Backups require their original
keys. Changing encryption configuration carelessly can make state unreadable.

For an existing plaintext state, follow the official fallback migration procedure
rather than copying this new-state example over it:
https://opentofu.org/docs/language/state/encryption/

Clean up each isolated directory with a reviewed `tofu destroy`. This lab does not
exercise remote locking, AWS KMS, Terraform migration, or real workload recovery.
