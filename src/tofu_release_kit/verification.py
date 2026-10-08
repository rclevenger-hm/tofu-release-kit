"""Revision-aware checks with a process deadline, including DNS resolution."""

import json
import subprocess
import sys
import time
from urllib.parse import urlsplit

from .io import KitError


def output_value(outputs, name):
    item = outputs.get(name)
    if not isinstance(item, dict) or item.get("sensitive") is not False:
        raise KitError("A required output is missing or sensitive")
    value = item.get("value")
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise KitError(
            "Required outputs must be nonempty strings of at most 2048 characters"
        )
    return value


def target_url(value, allow_http=False):
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as exc:
        raise KitError("Invalid verification URL") from exc
    if (
        url.scheme not in ("https", "http")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise KitError(
            "Verification URL must be HTTP(S), without credentials, query, or fragment"
        )
    if any(ord(c) < 33 for c in value) or port == 0:
        raise KitError("Invalid verification URL")
    if url.scheme == "http" and not allow_http:
        raise KitError(
            "Plain HTTP requires explicit allow_http = true for a trusted test endpoint"
        )
    return value


def probe(payload, timeout):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "tofu_release_kit.http_probe"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode:
            return {"passed": False, "reason": "probe_error"}
        data = json.loads(result.stdout)
        if type(data.get("passed")) is not bool or data.get("reason") not in {
            "verified",
            "status_mismatch",
            "revision_mismatch",
            "invalid_json",
            "response_too_large",
            "connection_error",
        }:
            raise ValueError
        return {"passed": data["passed"], "reason": data["reason"]}
    except subprocess.TimeoutExpired:
        return {"passed": False, "reason": "request_timeout"}
    except (OSError, ValueError, TypeError):
        return {"passed": False, "reason": "probe_error"}


def verify(config, outputs):
    prepared = []
    for check in config["verification"]:
        payload = {
            "url": target_url(
                output_value(outputs, check["url_from_output"]), check["allow_http"]
            ),
            "expected_status": check["expected_status"],
            "revision_field": check["revision_field"],
        }
        if "revision_from_output" in check:
            payload["expected_revision"] = output_value(
                outputs, check["revision_from_output"]
            )
        prepared.append((check, payload))
    results = []
    for check, payload in prepared:
        start = time.monotonic()
        deadline = start + check["timeout_seconds"]
        attempts = 0
        result = {"passed": False, "reason": "request_timeout"}
        while time.monotonic() < deadline:
            attempts += 1
            observation = probe(
                payload,
                max(
                    0.001,
                    min(check["request_timeout_seconds"], deadline - time.monotonic()),
                ),
            )
            # A final short deadline must not erase a useful observed failure.
            if observation["reason"] != "request_timeout" or attempts == 1:
                result = observation
            if result["passed"]:
                break
            time.sleep(
                max(0, min(check["interval_seconds"], deadline - time.monotonic()))
            )
        results.append(
            {
                "name": check["name"],
                **result,
                "attempts": attempts,
                "elapsed_seconds": round(time.monotonic() - start, 3),
            }
        )
    return {
        "schema_version": 1,
        "stack": config["stack"],
        "environment": config["environment"],
        "passed": bool(results) and all(item["passed"] for item in results),
        "checks": results,
    }
