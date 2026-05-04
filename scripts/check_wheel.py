"""Confirm the distributed wheel actually contains its policies and entry point."""

from pathlib import Path
from zipfile import ZipFile

(wheel,) = Path("dist").glob("*.whl")
with ZipFile(wheel) as archive:
    names = archive.namelist()
    assert "tofu_release_kit/policies/release.rego" in names
    assert "tofu_release_kit/cli.py" in names
    (entry,) = [name for name in names if name.endswith("entry_points.txt")]
    assert (
        "tofu-release-kit = tofu_release_kit.cli:main" in archive.read(entry).decode()
    )
print("Wheel contains the CLI and bundled policy implementation")
