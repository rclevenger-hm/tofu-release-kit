import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tofu_release_kit.cli import main

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_inspect_and_invalid_input_exit_codes(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            args = [
                "inspect",
                "--config",
                str(ROOT / "examples/demo/release-kit.toml"),
                "--plan",
                str(ROOT / "tests/fixtures/safe-plan.json"),
                "--output",
                str(Path(temp) / "report.json"),
            ]
            self.assertEqual(main(args), 0)
            self.assertEqual(
                json.loads((Path(temp) / "report.json").read_text())["counts"],
                {"create": 1},
            )
            args[4] = str(Path(temp) / "does-not-exist.json")
            self.assertEqual(main(args), 2)

    @unittest.skipUnless(shutil.which("opa"), "OPA required")
    def test_blocked_report_has_nonzero_exit_and_artifact(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            out = Path(temp) / "report.json"
            result = main(
                [
                    "report",
                    "--config",
                    str(ROOT / "examples/demo/release-kit.toml"),
                    "--plan",
                    str(ROOT / "tests/fixtures/protected-delete.json"),
                    "--output",
                    str(out),
                ]
            )
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(out.read_text())["status"], "blocked")
