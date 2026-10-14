"""Bounded input and private, atomic report output."""

import json
import os
import tempfile
from pathlib import Path

MAX_INPUT_BYTES = 16 * 1024 * 1024


class KitError(ValueError):
    """An actionable error safe to display without input contents."""


def validate_output_paths(inputs, outputs):
    """Reject accidental file aliases before work starts, without locking paths."""
    try:
        protected = [Path(path).resolve() for path in inputs]
        for path in outputs:
            target = Path(path).resolve()
            for other in protected:
                try:
                    aliases = target == other or target.samefile(other)
                except FileNotFoundError:
                    aliases = False
                if aliases:
                    raise KitError(
                        "Output paths must be distinct from input files and each other"
                    )
            protected.append(target)
    except (OSError, RuntimeError) as exc:
        raise KitError("Cannot resolve input and output paths") from exc


def read_json(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise KitError("JSON input exceeds the 16 MiB limit")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KitError("Cannot read valid JSON input") from exc
    if not isinstance(value, dict):
        raise KitError("JSON input must be an object")
    return value


def write_text(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, delete=False
        ) as stream:
            name = stream.name
            stream.write(content)
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def write_json(path, value):
    write_text(
        path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
