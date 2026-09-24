"""Attach the documented dated import using a normal merge, preserving current files."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args, capture=True):
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), *args],
            text=True,
            check=True,
            capture_output=capture,
        ).stdout.strip()
        if capture
        else subprocess.run(["git", "-C", str(ROOT), *args], check=True).returncode
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--push",
        action="store_true",
        help="Also fast-forward origin/main after the local merge",
    )
    args = parser.parse_args()
    if git("status", "--porcelain"):
        raise SystemExit("Commit or stash your local changes before importing history")
    if git("branch", "--show-current") != "main":
        raise SystemExit("Check out main first")
    origin = git("remote", "get-url", "origin").removesuffix(".git")
    if origin not in {
        "https://github.com/rclevenger-hm/tofu-release-kit",
        "git@github.com:rclevenger-hm/tofu-release-kit",
    }:
        raise SystemExit(
            "Unexpected origin; review this script for your fork before proceeding"
        )
    manifest = json.loads((ROOT / "history/import.json").read_text())
    bundle = ROOT / "history/initial-import.bundle"
    if hashlib.sha256(bundle.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise SystemExit("Bundle checksum mismatch")
    git("bundle", "verify", str(bundle))
    git("fetch", "origin", "main")
    git("merge", "--ff-only", "origin/main")
    git("fetch", str(bundle), "refs/heads/main:refs/heads/initial-import")
    if git("rev-parse", "initial-import") != manifest["head"]:
        raise SystemExit("Unexpected import head")
    already = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "merge-base",
            "--is-ancestor",
            "initial-import",
            "HEAD",
        ],
        check=False,
    )
    if already.returncode != 0:
        before = git("rev-parse", "HEAD^{tree}")
        git(
            "merge",
            "--allow-unrelated-histories",
            "--no-ff",
            "-s",
            "ours",
            "initial-import",
            "-m",
            "chore: attach documented synthetic initial import history",
        )
        assert git("rev-parse", "HEAD^{tree}") == before, (
            "Unexpected file changes during history merge"
        )
    if args.push:
        git("push", "origin", "HEAD:main", capture=False)
    else:
        print(
            "History attached locally. Review git log, then run git push origin HEAD:main"
        )


if __name__ == "__main__":
    main()
