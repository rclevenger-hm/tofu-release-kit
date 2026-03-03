"""Install checksum-verified pinned tools; Linux x86_64 CI only."""

import argparse
import hashlib
import io
import platform
import tarfile
import urllib.request
from pathlib import Path

OPA_VERSION = "1.21.1"
OPA_SHA256 = "668506eb17a2eaa1fce6cc0d1f42ef85125d4ac5bda5fc74d1152d0c77145031"
TOFU_VERSION = "1.13.1"
TOFU_SHA256 = "378ada19d4bc70c43732004e8159be771b23b9a5afdf059e5f8a2b3fa2c70a69"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(".tools"))
    parser.add_argument(
        "--tofu", action="store_true", help="Also install pinned OpenTofu"
    )
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "AMD64"}:
        raise SystemExit(
            "Install OPA 1.21.1 using its official release for your platform; this installer targets Linux x86_64."
        )
    target = args.directory / "opa"
    if (
        target.exists()
        and hashlib.sha256(target.read_bytes()).hexdigest() == OPA_SHA256
    ):
        target.chmod(0o755)
    else:
        url = f"https://github.com/open-policy-agent/opa/releases/download/v{OPA_VERSION}/opa_linux_amd64_static"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(100 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != OPA_SHA256:
            raise SystemExit("OPA checksum mismatch; refusing to install")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755)
    if args.tofu:
        url = f"https://github.com/opentofu/opentofu/releases/download/v{TOFU_VERSION}/tofu_{TOFU_VERSION}_linux_amd64.tar.gz"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(100 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != TOFU_SHA256:
            raise SystemExit("OpenTofu checksum mismatch; refusing to install")
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            binary = archive.extractfile("tofu").read()
        target = args.directory / "tofu"
        target.write_bytes(binary)
        target.chmod(0o755)


if __name__ == "__main__":
    main()
