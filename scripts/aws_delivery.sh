#!/usr/bin/env bash
set -euo pipefail
umask 077

stage="${1:?Expected plan or apply}"
case "$stage" in plan|apply) ;; *) exit 2 ;; esac
: "${STATE_BUCKET:?Set STATE_BUCKET}"
: "${STATE_KEY:?Set STATE_KEY}"
: "${STATE_KMS_KEY_ID:?Set STATE_KMS_KEY_ID}"
: "${GITHUB_SHA:?Run from the trusted workflow}"
: "${TRK_PLAN_KEY:?Set TRK_PLAN_KEY}"

repo_root="$PWD"
infra_root="$repo_root/examples/aws-serverless"
private="$repo_root/.artifacts/private"
config="$infra_root/release-kit.toml"
mkdir -p "$private"
python - <<'PY'
import json, os
from pathlib import Path
Path('.artifacts/private/backend.json').write_text(json.dumps({key: os.environ[key] for key in
    ('STATE_BUCKET', 'STATE_KEY', 'STATE_KMS_KEY_ID', 'AWS_REGION')}, sort_keys=True))
PY
python scripts/package_lambda.py
tofu -chdir="$infra_root" init -input=false -lockfile=readonly \
  -backend-config="bucket=$STATE_BUCKET" -backend-config="key=$STATE_KEY" \
  -backend-config="region=$AWS_REGION" -backend-config="kms_key_id=$STATE_KMS_KEY_ID" \
  -backend-config=encrypt=true -backend-config=use_lockfile=true > "$private/init.log" 2>&1 || {
    echo 'Backend initialization failed. Reproduce with restricted local credentials; private logs were not published.' >&2
    exit 2
  }
version="$(tofu version -json | python -c 'import json,sys; print(json.load(sys.stdin)["terraform_version"])')"

if [[ "$stage" == plan ]]; then
  tofu -chdir="$infra_root" plan -input=false -lock-timeout=60s -out="$private/plan.bin" > "$private/plan.log" 2>&1 || {
    echo 'Planning failed. Private plan diagnostics were not published.' >&2
    exit 2
  }
  tofu -chdir="$infra_root" show -json "$private/plan.bin" > "$private/plan.json" 2> "$private/show.log"
  python -m tofu_release_kit report --plan "$private/plan.json" --config "$config" \
    --commit "$GITHUB_SHA" --output .artifacts/review.json --markdown .artifacts/review.md
  python -m tofu_release_kit bind --plan "$private/plan.bin" --lockfile "$infra_root/.terraform.lock.hcl" \
    --config "$config" --commit "$GITHUB_SHA" --environment sandbox --tofu-version "$version" \
    --context "$private/backend.json" --output "$private/binding.json"
  python scripts/plan_artifact.py seal --directory "$private" --artifact .artifacts/plan.gpg
else
  python scripts/plan_artifact.py open --directory "$private" --artifact .artifacts/plan.gpg
  python -m tofu_release_kit check-binding --plan "$private/plan.bin" --lockfile "$infra_root/.terraform.lock.hcl" \
    --config "$config" --commit "$GITHUB_SHA" --environment sandbox --tofu-version "$version" \
    --context "$private/backend.json" --manifest "$private/binding.json" --output "$private/binding-check.json"
  tofu -chdir="$infra_root" show -json "$private/plan.bin" > "$private/plan.json" 2> "$private/show.log"
  python -m tofu_release_kit gate --plan "$private/plan.json" --config "$config" --output "$private/policy.json"
  apply_status=succeeded
  if ! tofu -chdir="$infra_root" apply -input=false -lock-timeout=60s "$private/plan.bin" > "$private/apply.log" 2>&1; then
    apply_status=failed
  fi
  verification_args=()
  if [[ "$apply_status" == succeeded ]]; then
    if tofu -chdir="$infra_root" output -json > "$private/outputs.json" 2> "$private/output.log"; then
      verify_exit=0
      python -m tofu_release_kit verify --config "$config" --outputs "$private/outputs.json" \
        --output "$private/verification.json" || verify_exit=$?
      if [[ "$verify_exit" -lt 2 ]]; then
        verification_args=(--verification "$private/verification.json")
      fi
    fi
  fi
  python -m tofu_release_kit report --plan "$private/plan.json" --config "$config" \
    --commit "$GITHUB_SHA" --apply-status "$apply_status" "${verification_args[@]}" \
    --output .artifacts/deployment.json --markdown .artifacts/deployment.md
fi
