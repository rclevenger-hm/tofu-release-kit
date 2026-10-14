import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tofu_release_kit.cli import main

ROOT = Path(__file__).resolve().parents[1]


class CLIPathTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = {}
        for name, content in {
            "config": (ROOT / "examples/demo/release-kit.toml").read_bytes(),
            "plan": (ROOT / "tests/fixtures/safe-plan.json").read_bytes(),
            "binary": b"synthetic saved plan",
            "lockfile": b"synthetic provider lockfile",
            "context": b'{"backend": "synthetic"}',
            "manifest": b'{"schema_version": 1}',
            "outputs": b'{"health_url": {"value": "http://127.0.0.1"}}',
            "verification": b'{"schema_version": 1}',
        }.items():
            path = self.root / name
            path.write_bytes(content)
            self.inputs[name] = path
        self.output = self.root / "result.json"
        self.markdown = self.root / "result.md"

    def arguments(self, command):
        args = [
            command,
            "--config",
            str(self.inputs["config"]),
            "--output",
            str(self.output),
        ]
        if command in {"bind", "check-binding"}:
            for flag, name in (
                ("plan", "binary"),
                ("lockfile", "lockfile"),
                ("context", "context"),
            ):
                args += ["--" + flag, str(self.inputs[name])]
            args += [
                "--commit",
                "a" * 40,
                "--environment",
                "demo",
                "--tofu-version",
                "1.13.1",
            ]
            if command == "check-binding":
                args += ["--manifest", str(self.inputs["manifest"])]
        elif command == "verify":
            args += ["--outputs", str(self.inputs["outputs"])]
        else:
            args += ["--plan", str(self.inputs["plan"])]
        if command == "report":
            args += [
                "--verification",
                str(self.inputs["verification"]),
                "--markdown",
                str(self.markdown),
            ]
        return args

    def replace_argument(self, args, flag, path):
        args[args.index("--" + flag) + 1] = str(path)

    def assert_rejected(self, args):
        before = {path: path.read_bytes() for path in self.inputs.values()}
        outputs_before = {
            path: path.read_bytes() if path.exists() else None
            for path in (self.output, self.markdown)
        }
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
            patch(
                "tofu_release_kit.cli.load_config",
                side_effect=AssertionError("Configuration read before path rejection"),
            ) as load,
            patch(
                "tofu_release_kit.cli.evaluate",
                side_effect=AssertionError("Policy evaluation before path rejection"),
            ) as evaluate,
            patch(
                "tofu_release_kit.cli.verify",
                side_effect=AssertionError("Verification before path rejection"),
            ) as verify,
        ):
            self.assertEqual(main(args), 2)
            load.assert_not_called()
            evaluate.assert_not_called()
            verify.assert_not_called()
        self.assertIn("error:", stderr.getvalue())
        self.assertNotIn(str(self.root), stderr.getvalue())
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        for path, content in outputs_before.items():
            if content is None:
                self.assertFalse(path.exists())
            else:
                self.assertEqual(path.read_bytes(), content)

    def test_output_cannot_replace_any_command_input(self):
        for command, names in {
            "inspect": ("config", "plan"),
            "gate": ("config", "plan"),
            "verify": ("config", "outputs"),
            "report": ("config", "plan", "verification"),
            "bind": ("config", "binary", "lockfile", "context"),
            "check-binding": ("config", "binary", "lockfile", "context", "manifest"),
        }.items():
            for name in names:
                with self.subTest(command=command, input=name):
                    args = self.arguments(command)
                    self.replace_argument(args, "output", self.inputs[name])
                    self.assert_rejected(args)

    def test_markdown_cannot_replace_any_report_input(self):
        for name in ("config", "plan", "verification"):
            with self.subTest(input=name):
                args = self.arguments("report")
                self.replace_argument(args, "markdown", self.inputs[name])
                self.assert_rejected(args)

    def test_relative_and_normalized_input_aliases_rejected(self):
        (self.root / "subdir").mkdir()
        plan = self.inputs["binary"]
        for alias in (
            os.path.relpath(plan),
            str(self.root) + "/./binary",
            str(self.root / "subdir") + "/../binary",
        ):
            with self.subTest(alias=alias):
                args = self.arguments("bind")
                self.replace_argument(args, "output", alias)
                self.assert_rejected(args)

    def test_symlink_and_hardlink_input_aliases_rejected(self):
        parent = self.root / "alias-parent"
        parent.symlink_to(self.root, target_is_directory=True)
        symbolic = self.root / "symbolic"
        symbolic.symlink_to(self.inputs["binary"])
        hard = self.root / "hard"
        hard.hardlink_to(self.inputs["binary"])
        for alias in (parent / "binary", symbolic, hard):
            with self.subTest(alias=alias):
                args = self.arguments("bind")
                self.replace_argument(args, "output", alias)
                self.assert_rejected(args)
                self.assertEqual(alias.read_bytes(), b"synthetic saved plan")
        self.assertTrue(symbolic.is_symlink())
        self.assertTrue(hard.samefile(self.inputs["binary"]))

    def test_output_collisions_rejected_before_either_output_is_written(self):
        parent = self.root / "alias-parent"
        parent.symlink_to(self.root, target_is_directory=True)
        for existing in (False, True):
            if existing:
                self.output.write_bytes(b"previous report")
            for alias in (
                self.output,
                os.path.relpath(self.output),
                parent / self.output.name,
            ):
                with self.subTest(existing=existing, alias=alias):
                    args = self.arguments("report")
                    self.replace_argument(args, "markdown", alias)
                    self.assert_rejected(args)

    def test_linked_output_collisions_leave_previous_artifacts_unchanged(self):
        self.output.write_bytes(b"previous report")
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    self.markdown.symlink_to(self.output)
                else:
                    self.markdown.hardlink_to(self.output)
                try:
                    self.assert_rejected(self.arguments("report"))
                    self.assertTrue(self.markdown.samefile(self.output))
                finally:
                    self.markdown.unlink()

    def test_unresolvable_path_returns_safe_input_error(self):
        loop = self.root / "private-loop"
        loop.symlink_to(loop)
        args = self.arguments("inspect")
        self.replace_argument(args, "output", loop)
        self.assert_rejected(args)
        self.assertTrue(loop.is_symlink())

    def test_unrelated_existing_output_is_still_replaced_privately(self):
        self.output.write_text("previous report")
        self.output.chmod(0o644)
        args = self.arguments("inspect")
        before = self.inputs["plan"].read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(self.output.read_text())["counts"], {"create": 1})
        self.assertEqual(self.inputs["plan"].read_bytes(), before)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_distinct_report_outputs_are_both_written(self):
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch(
                "tofu_release_kit.cli.evaluate",
                return_value={"allowed": True, "findings": []},
            ),
        ):
            self.assertEqual(main(self.arguments("report")), 0)
        self.assertEqual(json.loads(self.output.read_text())["status"], "reviewed")
        self.assertTrue(self.markdown.read_text().startswith("# Infrastructure"))
