"""Bind a reviewed plan to deployment inputs. This is integrity checking, not signing."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

from .io import KitError


def digest(path):
    try:
        with Path(path).open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise KitError("Cannot read a required binding input") from exc


def bind(
    plan, lockfile, config, commit, environment, tofu_version, now=None, context=None
):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise KitError("commit must be a full lowercase Git object ID")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", environment):
        raise KitError("Invalid binding environment")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][a-zA-Z0-9.-]+)?", tofu_version):
        raise KitError("Invalid OpenTofu version")
    return {
        "schema_version": 1,
        "commit": commit,
        "environment": environment,
        "tofu_version": tofu_version,
        "plan_sha256": digest(plan),
        "lockfile_sha256": digest(lockfile),
        "config_sha256": digest(config),
        "context_sha256": digest(context) if context else None,
        "created_at": (now or datetime.now(UTC)).isoformat(),
    }


def check_binding(manifest, expected, max_age_seconds=3600, now=None):
    if set(manifest) != set(expected):
        raise KitError("Invalid binding manifest fields")
    for key in expected:
        if key != "created_at" and manifest.get(key) != expected[key]:
            raise KitError(
                f"Plan binding mismatch: {key}; create and review a new plan"
            )
    try:
        created = datetime.fromisoformat(manifest["created_at"])
        if created.tzinfo is None:
            raise ValueError
        age = ((now or datetime.now(UTC)) - created).total_seconds()
    except (TypeError, ValueError) as exc:
        raise KitError("Invalid binding timestamp") from exc
    if not 0 <= age <= max_age_seconds:
        raise KitError(
            "Reviewed plan is expired or future-dated; create and review a new plan"
        )
    return {"schema_version": 1, "valid": True}
