"""Exercise state-preserving refactors and encryption recovery without cloud APIs."""

import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(directory, *args, env=None, expected=0):
    result = subprocess.run(
        ["tofu", f"-chdir={directory}", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != expected:
        raise RuntimeError(f"Local lab step failed: {args[0]} (diagnostics withheld)")
    return result.stdout


def main():
    source = ROOT / "examples/recovery-local"
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        shutil.copy(source / "main.tf", directory / "main.tf")
        run(directory, "init", "-input=false")
        run(directory, "apply", "-auto-approve", "-input=false")
        before = json.loads(run(directory, "show", "-json"))["values"]["root_module"][
            "resources"
        ][0]["values"]["id"]
        path = directory / "main.tf"
        path.write_text(
            path.read_text()
            .replace('"release"', '"deployment"')
            .replace("terraform_data.release", "terraform_data.deployment")
            + "\nmoved {\n from = terraform_data.release\n to = terraform_data.deployment\n}\n"
        )
        run(directory, "plan", "-input=false", "-out=refactor.bin")
        plan = json.loads(run(directory, "show", "-json", "refactor.bin"))
        assert all(
            r["change"]["actions"] == ["no-op"] for r in plan["resource_changes"]
        )
        run(directory, "apply", "-input=false", "refactor.bin")
        after = json.loads(run(directory, "show", "-json"))["values"]["root_module"][
            "resources"
        ][0]["values"]["id"]
        assert before == after
        run(directory, "destroy", "-auto-approve", "-input=false")
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        shutil.copy(source / "main.tf", directory / "main.tf")
        shutil.copy(source / "encryption.tf.example", directory / "encryption.tf")
        env = {**os.environ, "TF_VAR_state_passphrase": secrets.token_urlsafe(48)}
        run(directory, "init", "-input=false", env=env)
        run(directory, "apply", "-auto-approve", "-input=false", env=env)
        run(
            directory,
            "plan",
            "-input=false",
            env={**env, "TF_VAR_state_passphrase": "incorrect-key-that-is-long-enough"},
            expected=1,
        )
        run(directory, "plan", "-input=false", "-detailed-exitcode", env=env)
        run(directory, "destroy", "-auto-approve", "-input=false", env=env)
    print(
        "Local state refactor and encrypted-state key recovery passed; no cloud resources used"
    )


if __name__ == "__main__":
    main()
