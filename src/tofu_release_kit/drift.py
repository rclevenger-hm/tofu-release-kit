"""Read-only drift evidence from a plan; never infer drift from proposed changes."""

from datetime import UTC, datetime

from .io import KitError
from .plan import ACTIONS, summarize, validate_plan


def drift_report(config, plan_exit_code, plan=None):
    if type(plan_exit_code) is not int or plan_exit_code not in (0, 1, 2):
        raise KitError("Expected OpenTofu detailed exit code 0, 1, or 2")
    report = {
        "schema_version": 1,
        "stack": config["stack"],
        "environment": config["environment"],
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "managed_resources_in_supplied_state",
        "plan_exit_code": plan_exit_code,
        "plan_result": {0: "no_changes", 1: "error", 2: "changes"}[plan_exit_code],
        "status": "plan_error",
        "drift": None,
        "changed_outputs": None,
    }
    if plan_exit_code == 1:
        if plan is not None:
            raise KitError("Do not supply a saved plan after a failed planning run")
        return report
    if not isinstance(plan, dict):
        raise KitError(
            "A saved-plan JSON document is required after successful planning"
        )
    for flag in ("complete", "errored"):
        if flag in plan and type(plan[flag]) is not bool:
            raise KitError("Plan completion and error flags must be boolean")
    validate_plan(plan)
    # resource_drift describes observed changes since the previous state.
    # resource_changes instead describes the proposed reconciliation/configuration.
    observed = {**plan, "resource_changes": plan.get("resource_drift", [])}
    validate_plan(observed)
    observed["resource_changes"] = [
        resource
        for resource in observed["resource_changes"]
        if resource["mode"] == "managed"
    ]
    drift = summarize(observed)
    outputs = plan.get("output_changes", {})
    if not isinstance(outputs, dict):
        raise KitError("output_changes must be an object")
    changed_outputs = 0
    for change in outputs.values():
        if (
            not isinstance(change, dict)
            or not isinstance(change.get("actions"), list)
            or any(not isinstance(action, str) for action in change["actions"])
            or tuple(change["actions"]) not in ACTIONS
        ):
            raise KitError("Invalid output change action list")
        changed_outputs += change["actions"] != ["no-op"]
    planned_changes = any(
        resource["change"]["actions"] != ["no-op"]
        for resource in plan.get("resource_changes", [])
    )
    if plan_exit_code == 0 and (planned_changes or changed_outputs):
        raise KitError("Plan changes conflict with detailed exit code 0")
    # A normal plan can observe drift without proposing changes (e.g. ignore_changes).
    # Conversely, exit 2 alone is not evidence of managed-resource drift.
    status = "no_changes"
    if drift["resources"]:
        status = "drift_detected"
    elif plan_exit_code == 2:
        status = "changes_detected"
    report.update(status=status, drift=drift, changed_outputs=changed_outputs)
    return report
