# Terraform to OpenTofu migration exercise

Use the official version-specific guide:
https://opentofu.org/docs/intro/migration/migration-guide/

Do this on disposable infrastructure first. This repository does not claim a
universal migration guarantee for every Terraform version, backend, or provider.

1. Record the Terraform version, providers, dependency lockfile, backend, resource
   IDs, state lineage/serial, and interdependent consumers of remote state.
2. Stop concurrent writers. Back up code, lockfile, and state with restricted access.
   Do not commit state or a real plan to Git.
3. Obtain a no-change Terraform plan. Resolve unexplained drift before migration.
4. Follow the official guide for the starting version. Initialize OpenTofu with
   compatible provider versions and the same backend. Review dependency changes.
5. Obtain a no-change OpenTofu plan, compare resource identities, and run application
   health checks. Do not combine migration with refactoring or provider upgrades.
6. Make one small reversible change, apply it, and verify the application.
7. Document the migration evidence and operational owner before changing CI.

Reverting to Terraform is a separate compatibility decision. OpenTofu-specific
state formats/features, encryption, or provider changes may need explicit conversion
and testing. Do not assume replacing the executable reverses a migration. After
resources have changed, restoring an old state snapshot is not a safe rollback.

The local recovery example uses the built-in terraform_data resource and can serve
as a simple starting configuration. Run it with an appropriate compatible Terraform
version first when exercising migration. The automated CI validates only OpenTofu;
it does not claim to certify Terraform migration compatibility.
