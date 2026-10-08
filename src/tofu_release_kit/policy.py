"""OPA is the sole policy evaluator; unavailable or malformed evaluation fails closed."""

import json
import subprocess
from importlib.resources import files

from .io import KitError
from .plan import validate_plan


def evaluate(plan, config, opa="opa"):
    validate_plan(plan)
    bundle = files("tofu_release_kit").joinpath("policies")
    try:
        process = subprocess.run(
            [
                opa,
                "eval",
                "--strict",
                "--format=json",
                "--stdin-input",
                "--data",
                str(bundle),
                "data.tofu_release_kit.decision",
            ],
            input=json.dumps({"plan": plan, "config": config["policies"]}),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KitError(
            "OPA unavailable or timed out; policy evaluation failed closed"
        ) from exc
    if process.returncode:
        raise KitError(
            "OPA evaluation failed; run opa check on the installed policy bundle"
        )
    try:
        decision = json.loads(process.stdout)["result"][0]["expressions"][0]["value"]
        if (
            not isinstance(decision, dict)
            or type(decision["allowed"]) is not bool
            or not isinstance(decision["findings"], list)
        ):
            raise ValueError
        findings = []
        for item in decision["findings"]:
            if set(item) != {"rule", "address", "reason"} or any(
                not isinstance(v, str) for v in item.values()
            ):
                raise ValueError
            findings.append({key: item[key] for key in ("rule", "address", "reason")})
        if decision["allowed"] != (len(findings) == 0):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise KitError(
            "OPA returned an invalid decision; policy evaluation failed closed"
        ) from exc
    return {
        "schema_version": 1,
        "allowed": decision["allowed"],
        "findings": sorted(
            findings, key=lambda f: (f["address"], f["rule"], f["reason"])
        ),
    }
