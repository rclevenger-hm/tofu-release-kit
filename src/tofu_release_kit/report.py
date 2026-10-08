"""Reports carry allowlisted metadata and separate apply from service health."""

import re
from datetime import UTC, datetime
from html import escape

from .io import KitError


def deployment_report(
    config, summary, decision, apply_status, verification=None, commit=None
):
    if apply_status != "succeeded" or not decision.get("allowed"):
        verification = None
    if commit is not None and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise KitError("Report commit must be a full Git object ID")
    if apply_status not in {"not_run", "succeeded", "failed"}:
        raise KitError("Invalid apply status")
    if type(decision.get("allowed")) is not bool or not isinstance(
        decision.get("findings"), list
    ):
        raise KitError("Invalid policy result")
    status = "blocked" if not decision["allowed"] else "reviewed"
    if decision["allowed"] and apply_status == "failed":
        status = "apply_failed"
    if decision["allowed"] and apply_status == "succeeded":
        status = "unverified"
        if verification is not None:
            if (
                verification.get("stack") != config["stack"]
                or verification.get("environment") != config["environment"]
            ):
                raise KitError(
                    "Verification result belongs to another stack or environment"
                )
            checks = verification.get("checks")
            if not isinstance(checks, list) or any(
                not isinstance(x, dict) for x in checks
            ):
                raise KitError("Invalid verification check results")
            if any(not isinstance(x.get("name"), str) for x in checks) or {
                x.get("name") for x in checks
            } != {x["name"] for x in config["verification"]}:
                raise KitError("Verification results do not match configured checks")
            if len(checks) != len(config["verification"]) or any(
                type(x.get("passed")) is not bool for x in checks
            ):
                raise KitError("Invalid verification check results")
            passed = all(x["passed"] for x in checks)
            if (
                type(verification.get("passed")) is not bool
                or verification["passed"] != passed
            ):
                raise KitError("Inconsistent verification result")
            reasons = {
                "verified",
                "status_mismatch",
                "revision_mismatch",
                "invalid_json",
                "response_too_large",
                "connection_error",
                "request_timeout",
                "probe_error",
            }
            for check in checks:
                if (
                    not isinstance(check.get("reason"), str)
                    or check["reason"] not in reasons
                ):
                    raise KitError("Invalid verification reason")
                if type(check.get("attempts")) is not int or check["attempts"] < 1:
                    raise KitError("Invalid verification attempt count")
                if check["passed"] != (check["reason"] == "verified"):
                    raise KitError("Inconsistent verification reason")
            verification = {
                "schema_version": 1,
                "stack": config["stack"],
                "environment": config["environment"],
                "passed": passed,
                "checks": [
                    {k: x[k] for k in ("name", "passed", "reason", "attempts")}
                    for x in checks
                ],
            }
            status = "verified" if passed else "verification_failed"
    return {
        "schema_version": 1,
        "stack": config["stack"],
        "environment": config["environment"],
        "commit": commit,
        "created_at": datetime.now(UTC).isoformat(),
        "status": status,
        "apply_status": apply_status,
        "plan": summary,
        "policy": decision,
        "verification": verification,
    }


def cell(value):
    return (
        escape(str(value))
        .replace("|", "&#124;")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("`", "&#96;")
    )


def markdown(report):
    lines = [
        "# Infrastructure deployment report",
        "",
        f"**Status:** {cell(report['status'])}",
        "",
        f"Stack: {cell(report['stack'])} · Environment: {cell(report['environment'])}",
        "",
        f"Apply: {cell(report['apply_status'])}",
        "",
        "## Changes",
        "",
        "| Resource | Action |",
        "| --- | --- |",
    ]
    for resource in report["plan"]["resources"]:
        lines.append(f"| {cell(resource['address'])} | {cell(resource['action'])} |")
    lines += [
        "",
        "## Policy",
        "",
        "Allowed" if report["policy"]["allowed"] else "Blocked",
    ]
    for finding in report["policy"]["findings"]:
        lines.append(
            f"- {cell(finding['rule'])}: {cell(finding['address'])} — {cell(finding['reason'])}"
        )
    if report["verification"]:
        lines += ["", "## Verification", ""]
        for check in report["verification"]["checks"]:
            lines.append(
                f"- {cell(check['name'])}: {cell(check['reason'])} ({check['attempts']} attempts)"
            )
    lines += [
        "",
        "This report is operational evidence, not a signed attestation or proof of compliance.",
        "",
    ]
    return "\n".join(lines)
