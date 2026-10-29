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
    def test_inspect_recovery_plan_preserves_object_identity(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            out = Path(temp) / "summary.json"
            self.assertEqual(
                main(
                    [
                        "inspect",
                        "--config",
                        str(ROOT / "examples/demo/release-kit.toml"),
                        "--plan",
                        str(ROOT / "tests/fixtures/deposed-recovery.json"),
                        "--output",
                        str(out),
                    ]
                ),
                0,
            )
            result = json.loads(out.read_text())
            self.assertEqual(result["counts"], {"delete": 1, "unchanged": 1})
            self.assertEqual(result["resources"][0]["deposed"], "deadbeef")

    @unittest.skipUnless(shutil.which("opa"), "OPA required")
    def test_recovery_gate_and_report_keep_protected_deletions_blocked(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            for command in ("gate", "report"):
                with self.subTest(command=command):
                    out = Path(temp) / (command + ".json")
                    args = [
                        command,
                        "--config",
                        str(ROOT / "examples/demo/release-kit.toml"),
                        "--plan",
                        str(ROOT / "tests/fixtures/deposed-recovery.json"),
                        "--output",
                        str(out),
                    ]
                    md = Path(temp) / "report.md"
                    if command == "report":
                        args += ["--markdown", str(md)]
                    self.assertEqual(main(args), 1)
                    result = json.loads(out.read_text())
                    decision = result if command == "gate" else result["policy"]
                    self.assertFalse(decision["allowed"])
                    self.assertEqual(
                        decision["findings"][0]["rule"], "protected-resource"
                    )
                    self.assertNotIn("DO_NOT_PUBLISH", out.read_text())
                    if command == "report":
                        self.assertEqual(result["status"], "blocked")
                        self.assertIn("(deposed deadbeef)", md.read_text())

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
