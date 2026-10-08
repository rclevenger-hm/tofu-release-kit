# AWS sandbox setup

This example has **not been deployed to your AWS account by the repository setup**.
Local validation uses mocked providers. Configure and validate the live workflow
in a dedicated sandbox before adopting it for important infrastructure.

The example exposes a small public GET /health endpoint through API Gateway and
Lambda. It reports its revision and uses a narrowly scoped DescribeTable call to
check DynamoDB availability. It accepts no customer writes. It demonstrates
dependency readiness, not an end-to-end data transaction. Costs can include API
requests, Lambda, DynamoDB backups, logs, KMS, and state storage. Concurrency and
API throttling are capped. Set an account budget and destroy the demo when finished.

## Prerequisites

1. Existing S3 state bucket with versioning and block-public-access enabled, plus
   a KMS key. Keep the backend outside the application state to avoid self-destruction.
2. GitHub OIDC provider in the sandbox AWS account.
3. A read-oriented planning role and a separate deployment role. Both need scoped
   backend reads and writes to the `.tflock` object, and the necessary KMS access.
   The apply role also needs writes to its state object and resource provisioning.
4. A GitHub Environment named `sandbox`, with required reviewers and default-branch
   restrictions. Verify that your repository plan supports the required protection.
5. Default-branch protection and review requirements for workflows, policy, and
   deployment configuration.

The plan role trust should require `aud=sts.amazonaws.com` and the exact subject
`repo:OWNER/REPO:ref:refs/heads/main` (substitute your default branch). The apply
role should require `repo:OWNER/REPO:environment:sandbox`. Do not use organization-
wide wildcard trust. Separate roles are useful only when their permissions differ.

## Repository settings

| Kind | Name | Value |
| --- | --- | --- |
| Variable | AWS_REGION | Example: us-east-2 |
| Variable | AWS_PLAN_ROLE_ARN | Scoped planning role |
| Variable | AWS_APPLY_ROLE_ARN | Scoped deployment role |
| Variable | STATE_BUCKET | Existing versioned state bucket |
| Variable | STATE_KEY | Example: tofu-release-kit/sandbox.tfstate |
| Variable | STATE_KMS_KEY_ID | Backend KMS key ARN |
| Variable | INFRA_OWNER | Accountable team name |
| Secret | TRK_PLAN_KEY | Random single-line secret, at least 32 characters |

Use a cryptographic generator for the plan key and store it directly in repository
secrets. Do not place it in a workflow input, configuration file, or issue.

The application role is defined in main.tf with DescribeTable on its one table
and log writes to its one log group. The workflow deployment role needs permissions
for the resources in that file: DynamoDB, Lambda, its execution role and inline
policy, API Gateway, and CloudWatch. Scope supported resource ARNs to `trk-sandbox`
names and restrict `iam:PassRole` to the Lambda execution role and service. Some
list/create APIs need wildcard resources; constrain them using supported conditions.
Have the sandbox account administrator review this role; do not attach AdministratorAccess.

## Run

Run **AWS reference delivery** manually from the default branch. The plan job
creates a report. Read the changed resources and policy result, then approve the
`sandbox` environment deployment within one hour. The apply job verifies the plan
binding, applies that plan, and checks readiness plus revision. Failed verification
leaves the actual infrastructure available for investigation.

The workflow intentionally hides raw OpenTofu logs because they can contain secret
values. To diagnose provider/backend errors, reproduce the command with restricted
local credentials; never paste raw state or plans into public GitHub logs or issues.

## Local execution and cleanup

```sh
python scripts/package_lambda.py
cp examples/aws-serverless/backend.hcl.example /tmp/trk-backend.hcl
# Edit that file to use the dedicated sandbox backend.
export TF_VAR_owner=platform
export TF_VAR_application_revision="$(git rev-parse HEAD)"
tofu -chdir=examples/aws-serverless init -backend-config=/tmp/trk-backend.hcl
tofu -chdir=examples/aws-serverless plan
```

To clean up, inspect the sandbox account and backend selection, create an explicit
destroy plan, review it, and apply it locally. The normal delivery policy will block
the protected table's deletion; a maintainer must deliberately authorize demo
teardown separately. Remove the application resources before deleting backend
storage or keys. The CloudWatch alarm records errors but has no notification target
until an operator adds one.
