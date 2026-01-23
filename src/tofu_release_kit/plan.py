"""Validate plan structure and extract only allowlisted change metadata."""

from collections import Counter

from .io import KitError

ACTIONS = {
    ("no-op",): "unchanged",
    ("create",): "create",
    ("update",): "update",
    ("delete",): "delete",
    ("delete", "create"): "replace",
    ("create", "delete"): "replace",
    ("read",): "read",
    ("forget",): "forget",
    ("create", "forget"): "replace",
}


def validate_plan(plan):
    version = plan.get("format_version", "")
    if not isinstance(version, str) or version.split(".")[0] != "1":
        raise KitError("Unsupported plan JSON format_version; expected major version 1")
    if plan.get("errored") is True:
        raise KitError("The plan reports an error")
    if plan.get("complete") is False or plan.get("deferred_changes"):
        raise KitError("Deferred or incomplete plans require manual review")
    if "planned_values" not in plan or not isinstance(plan["planned_values"], dict):
        raise KitError("Expected a saved plan JSON document, not state JSON")
    changes = plan.get("resource_changes", [])
    if not isinstance(changes, list):
        raise KitError("resource_changes must be a list")
    seen = set()
    for resource in changes:
        if not isinstance(resource, dict):
            raise KitError("Invalid resource change")
        for field in ("address", "type", "mode"):
            if (
                not isinstance(resource.get(field), str)
                or not resource[field]
                or len(resource[field]) > 1024
            ):
                raise KitError("Resource metadata is missing or invalid")
        if resource["mode"] not in ("managed", "data") or resource["address"] in seen:
            raise KitError("Unexpected resource mode or duplicate resource address")
        seen.add(resource["address"])
        change = resource.get("change")
        if not isinstance(change, dict) or not isinstance(change.get("actions"), list):
            raise KitError("Resource change has no valid action list")
        if (
            any(not isinstance(action, str) for action in change["actions"])
            or tuple(change["actions"]) not in ACTIONS
        ):
            raise KitError(
                "Unsupported resource action; update the toolkit before proceeding"
            )
        for field in ("before", "after"):
            if change.get(field) is not None and not isinstance(change[field], dict):
                raise KitError("Resource before/after values must be objects or null")
        if any(
            a in change["actions"] for a in ("create", "update", "no-op")
        ) and not isinstance(change.get("after"), dict):
            raise KitError("Planned resource values are missing")
        if not isinstance(change.get("after_unknown", {}), (dict, bool)):
            raise KitError("Invalid unknown-value metadata")
    return plan


def summarize(plan):
    validate_plan(plan)
    resources = []
    counts = Counter()
    for resource in plan.get("resource_changes", []):
        kind = ACTIONS[tuple(resource["change"]["actions"])]
        counts[kind] += 1
        if kind != "unchanged":
            resources.append(
                {
                    "address": resource["address"],
                    "type": resource["type"],
                    "action": kind,
                }
            )
    return {
        "schema_version": 1,
        "counts": dict(sorted(counts.items())),
        "resources": sorted(resources, key=lambda x: x["address"]),
    }
