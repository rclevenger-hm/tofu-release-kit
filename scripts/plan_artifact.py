"""Encrypt or decrypt a saved plan plus its binding for transfer between trusted jobs."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

MEMBERS = ("plan.bin", "binding.json")


def transfer(mode, directory, artifact, key):
    if len(key) < 32 or "\n" in key or "\r" in key:
        raise ValueError(
            "TRK_PLAN_KEY must be a single-line random secret of at least 32 characters"
        )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp) / "gnupg"
        home.mkdir(mode=0o700)
        archive = Path(temp) / "payload.zip"
        if mode == "seal":
            with ZipFile(archive, "w", compression=ZIP_STORED) as payload:
                for name in MEMBERS:
                    source = directory / name
                    if source.stat().st_size > 64 * 1024 * 1024:
                        raise ValueError("Plan payload exceeds the 64 MiB member limit")
                    payload.write(source, arcname=name)
        args = [
            "gpg",
            "--homedir",
            str(home),
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--no-symkey-cache",
            "--passphrase-fd",
            "0",
        ]
        if mode == "seal":
            args += [
                "--cipher-algo",
                "AES256",
                "--s2k-mode",
                "3",
                "--s2k-count",
                "65011712",
                "--output",
                str(artifact),
                "--symmetric",
                str(archive),
            ]
        else:
            args += ["--output", str(archive), "--decrypt", str(artifact)]
        result = subprocess.run(
            args,
            input=key + "\n",
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode:
            raise ValueError(
                "Encrypted plan transfer failed; check the key and artifact integrity"
            )
        if mode == "open":
            directory.mkdir(parents=True, exist_ok=True)
            with ZipFile(archive) as payload:
                if sorted(payload.namelist()) != sorted(MEMBERS):
                    raise ValueError("Unexpected encrypted payload contents")
                for name in MEMBERS:
                    if payload.getinfo(name).file_size > 64 * 1024 * 1024:
                        raise ValueError("Plan payload exceeds the 64 MiB member limit")
                    target = directory / name
                    with target.open("wb") as stream:
                        os.chmod(target, 0o600)
                        stream.write(payload.read(name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["seal", "open"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    args = parser.parse_args()
    try:
        transfer(
            args.mode, args.directory, args.artifact, os.environ.get("TRK_PLAN_KEY", "")
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise SystemExit(
            "Plan artifact operation failed; no plaintext diagnostic was emitted"
        )


if __name__ == "__main__":
    main()
