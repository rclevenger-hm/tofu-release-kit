"""Strict versioned TOML configuration, using the Python standard library."""

import re
import tomllib
from pathlib import Path

from .io import KitError

TAGGABLE_TYPES = [
    "aws_lambda_function",
    "aws_dynamodb_table",
    "aws_cloudwatch_log_group",
    "aws_apigatewayv2_api",
    "aws_s3_bucket",
]


def keys(value, allowed, context):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise KitError(
            f"Unexpected fields in {context}; check the configuration reference"
        )


def strings(value, context):
    if not isinstance(value, list) or any(
        not isinstance(x, str) or not x.strip() for x in value
    ):
        raise KitError(f"{context} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise KitError(f"{context} contains duplicate values")
    return value


def number(value, low, high, context):
    if type(value) not in (int, float) or not low <= value <= high:
        raise KitError(f"{context} must be between {low} and {high}")
    return value


def validate_config(data):
    keys(
        data,
        {"schema_version", "stack", "environment", "policies", "verification"},
        "configuration",
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise KitError("Only configuration schema_version = 1 is supported")
    for name in ("stack", "environment"):
        if not isinstance(data.get(name), str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,80}", data[name]
        ):
            raise KitError(
                f"{name} must be 1–80 letters, numbers, underscores, or hyphens"
            )
    policies = data.get("policies", {})
    keys(
        policies,
        {"required_tags", "protected_resources", "taggable_types", "admin_ports"},
        "policies",
    )
    policy = {
        "required_tags": strings(
            policies.get("required_tags", ["owner", "environment"]), "required_tags"
        ),
        "protected_resources": strings(
            policies.get("protected_resources", []), "protected_resources"
        ),
        "taggable_types": strings(
            policies.get("taggable_types", TAGGABLE_TYPES), "taggable_types"
        ),
        "admin_ports": policies.get("admin_ports", [22, 3389]),
    }
    if not isinstance(policy["admin_ports"], list) or any(
        type(p) is not int or not 1 <= p <= 65535 for p in policy["admin_ports"]
    ):
        raise KitError("admin_ports must contain integer ports from 1 to 65535")
    checks = data.get("verification", [])
    if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
        raise KitError("Configure between 1 and 20 verification checks")
    normalized = []
    for item in checks:
        keys(
            item,
            {
                "name",
                "url_from_output",
                "expected_status",
                "revision_from_output",
                "revision_field",
                "timeout_seconds",
                "request_timeout_seconds",
                "interval_seconds",
                "allow_http",
            },
            "verification",
        )
        for field in ("name", "url_from_output"):
            if not isinstance(item.get(field), str) or not re.fullmatch(
                r"[a-zA-Z0-9_-]{1,80}", item[field]
            ):
                raise KitError(
                    f"verification.{field} must be a simple nonempty identifier"
                )
        if (
            type(item.get("expected_status", 200)) is not int
            or not 200 <= item.get("expected_status", 200) <= 299
        ):
            raise KitError("expected_status must be a 2xx integer")
        if type(item.get("allow_http", False)) is not bool:
            raise KitError("allow_http must be a boolean")
        check = {
            "expected_status": 200,
            "timeout_seconds": 120,
            "request_timeout_seconds": 5,
            "interval_seconds": 2,
            "allow_http": False,
            "revision_field": "revision",
            **item,
        }
        for field, low, high in (
            ("timeout_seconds", 0.05, 600),
            ("request_timeout_seconds", 0.01, 30),
            ("interval_seconds", 0.01, 30),
        ):
            number(check[field], low, high, field)
        for field in ("revision_from_output", "revision_field"):
            if field in check and (
                not isinstance(check[field], str)
                or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", check[field])
            ):
                raise KitError(f"{field} must be a simple identifier")
        normalized.append(check)
    if len({x["name"] for x in normalized}) != len(normalized):
        raise KitError("Verification names must be unique")
    return {
        "schema_version": 1,
        "stack": data["stack"],
        "environment": data["environment"],
        "policies": policy,
        "verification": normalized,
    }


def load_config(path):
    try:
        with Path(path).open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise KitError("Cannot read valid TOML configuration") from exc
    return validate_config(data)
