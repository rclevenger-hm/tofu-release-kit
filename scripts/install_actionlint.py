"""Install the verified Linux x86_64 workflow linter used by CI."""

import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path

VERSION = "1.7.12"
SHA256 = "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
url = f"https://github.com/rhysd/actionlint/releases/download/v{VERSION}/actionlint_{VERSION}_linux_amd64.tar.gz"
with urllib.request.urlopen(url, timeout=60) as response:
    data = response.read(20 * 1024 * 1024)
if hashlib.sha256(data).hexdigest() != SHA256:
    raise SystemExit("actionlint checksum mismatch")
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    binary = archive.extractfile("actionlint").read()
target = Path(".tools/actionlint")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(binary)
target.chmod(0o755)
