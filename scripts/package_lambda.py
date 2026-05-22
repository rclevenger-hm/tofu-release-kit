"""Produce byte-identical Lambda packages for matching source commits."""

import argparse
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


def package(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_STORED) as archive:
        entry = ZipInfo("handler.py", date_time=(2020, 1, 1, 0, 0, 0))
        entry.external_attr = 0o644 << 16
        entry.create_system = 3
        archive.writestr(entry, source.read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("examples/aws-serverless"))
    args = parser.parse_args()
    package(args.root / "app/handler.py", args.root / ".artifacts/function.zip")
