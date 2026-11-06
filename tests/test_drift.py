import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import config, plan, recovery_plan

from tofu_release_kit.cli import main
from tofu_release_kit.drift import drift_report
from tofu_release_kit.io import KitError

ROOT = Path(__file__).resolve().parents[1]


def empty_plan():
    return {"format_version": "1.2", "planned_values": {}}


def observed_plan(actions=None):
    return {
        **empty_plan(),
        "resource_drift": plan(actions or ["update"])["resource_changes"],
    }


class DriftTests(unittest.TestCase):
    def test_clean_snapshot_and_plan_failure_are_distinct(self):
        clean = drift_report(config(), 0, empty_plan())
        self.assertEqual(clean["status"], "no_changes")
        self.assertEqual(clean["drift"]["resources"], [])
        failed = drift_report(config(), 1)
        self.assertEqual(failed["status"], "plan_error")
        self.assertIsNone(failed["drift"])
        self.assertIsNone(failed["changed_outputs"])

    def test_managed_drift_is_separate_from_proposed_changes(self):
        for action in ("update", "delete"):
            with self.subTest(action=action):
                data = observed_plan([action])
                if action == "delete":
                    data["resource_drift"][0]["change"]["after"] = None
                report = drift_report(config(), 2, data)
                self.assertEqual(report["status"], "drift_detected")
                self.assertEqual(report["drift"]["counts"], {action: 1})
                self.assertEqual(report["plan_result"], "changes")
        # A normal refreshed plan can observe ignored drift without proposing changes.
        report = drift_report(config(), 0, observed_plan())
        self.assertEqual(report["status"], "drift_detected")
        self.assertEqual(report["plan_result"], "no_changes")

    def test_configuration_changes_and_empty_exit_two_are_never_clean(self):
        for data in (plan(), empty_plan()):
            with self.subTest(data=data):
                report = drift_report(config(), 2, data)
                self.assertEqual(report["status"], "changes_detected")
                self.assertEqual(report["drift"]["resources"], [])

    def test_data_sources_and_noops_are_not_managed_drift(self):
        data = observed_plan()
        data["resource_drift"][0]["mode"] = "data"
        report = drift_report(config(), 2, data)
        self.assertEqual(report["status"], "changes_detected")
        self.assertEqual(report["drift"]["counts"], {})
        report = drift_report(config(), 0, observed_plan(["no-op"]))
        self.assertEqual(report["status"], "no_changes")

    def test_output_only_changes_are_counted_without_names_or_values(self):
        data = empty_plan()
        data["output_changes"] = {
            "PRIVATE_OUTPUT_NAME": {
                "actions": ["update"],
                "before": "PRIVATE_VALUE",
                "after": "PRIVATE_NEW_VALUE",
                "after_sensitive": True,
            },
            "other": {"actions": ["no-op"]},
        }
        report = drift_report(config(), 2, data)
        self.assertEqual(report["status"], "changes_detected")
        self.assertEqual(report["changed_outputs"], 1)
        self.assertNotIn("PRIVATE_", json.dumps(report))
        with self.assertRaises(KitError):
            drift_report(config(), 0, data)

    def test_values_and_diagnostics_are_never_copied(self):
        data = observed_plan()
        data.update(
            diagnostics="DO_NOT_PUBLISH", variables={"secret": "DO_NOT_PUBLISH"}
        )
        self.assertNotIn("DO_NOT_PUBLISH", json.dumps(drift_report(config(), 2, data)))

    def test_deposed_object_identity_and_sort_order_are_preserved(self):
        data = empty_plan()
        data["resource_drift"] = recovery_plan()["resource_changes"]
        report = drift_report(config(), 2, data)
        resources = report["drift"]["resources"]
        self.assertTrue(any("deposed" in resource for resource in resources))
        data["resource_drift"].reverse()
        self.assertEqual(
            drift_report(config(), 2, data)["drift"]["resources"], resources
        )

    def test_invalid_exit_codes_or_failed_run_with_stale_plan_are_rejected(self):
        for code in (True, False, -1, 3, "2", None):
            with self.subTest(code=code), self.assertRaises(KitError):
                drift_report(config(), code, empty_plan())
        with self.assertRaises(KitError):
            drift_report(config(), 1, empty_plan())
        for code in (0, 2):
            with self.subTest(code=code), self.assertRaises(KitError):
                drift_report(config(), code)
        with self.assertRaises(KitError):
            drift_report(config(), 0, plan())

    def test_malformed_drift_and_output_changes_fail_closed(self):
        for value in (None, {}, "bad", [None]):
            with self.subTest(value=value), self.assertRaises(KitError):
                drift_report(config(), 0, {**empty_plan(), "resource_drift": value})
        for change in ({}, {"actions": []}, {"actions": ["future"]}, {"actions": [{}]}):
            with self.subTest(change=change), self.assertRaises(KitError):
                drift_report(
                    config(), 2, {**empty_plan(), "output_changes": {"x": change}}
                )
        with self.assertRaises(KitError):
            drift_report(config(), 0, {**empty_plan(), "output_changes": []})
        for field, value in (("mode", "unknown"), ("address", ""), ("change", {})):
            data = observed_plan()
            data["resource_drift"][0][field] = value
            with self.subTest(field=field), self.assertRaises(KitError):
                drift_report(config(), 2, data)
        data = observed_plan()
        data["resource_drift"] *= 2
        with self.assertRaises(KitError):
            drift_report(config(), 2, data)

    def test_incomplete_errored_and_invalid_plans_fail_closed(self):
        for updates in (
            {"complete": False},
            {"complete": "true"},
            {"errored": True},
            {"errored": 0},
            {"deferred_changes": [{}]},
            {"format_version": "2.0"},
            {"planned_values": None},
        ):
            with self.subTest(updates=updates), self.assertRaises(KitError):
                drift_report(config(), 0, {**empty_plan(), **updates})
        original = observed_plan()
        data = copy.deepcopy(original)
        drift_report(config(), 2, data)
        self.assertEqual(data, original)


class DriftCLITests(unittest.TestCase):
    def run_drift(self, directory, code, data=None, extra=()):
        args = [
            "drift",
            "--config",
            str(ROOT / "examples/demo/release-kit.toml"),
            "--plan-exit-code",
            str(code),
            "--output",
            str(directory / "report.json"),
        ]
        if data is not None:
            (directory / "plan.json").write_text(json.dumps(data))
            args += ["--plan", str(directory / "plan.json")]
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
            patch(
                "tofu_release_kit.cli.evaluate", side_effect=AssertionError("No OPA")
            ),
        ):
            return main(args + list(extra))

    def test_toolkit_codes_and_private_artifact(self):
        for code, data, expected, status in (
            (0, empty_plan(), 0, "no_changes"),
            (1, None, 2, "plan_error"),
            (2, observed_plan(), 1, "drift_detected"),
            (2, empty_plan(), 1, "changes_detected"),
            (0, observed_plan(), 1, "drift_detected"),
        ):
            with (
                self.subTest(code=code, status=status),
                tempfile.TemporaryDirectory() as temp,
            ):
                directory = Path(temp)
                self.assertEqual(self.run_drift(directory, code, data), expected)
                output = directory / "report.json"
                self.assertEqual(json.loads(output.read_text())["status"], status)
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_error_does_not_read_a_stale_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.assertEqual(
                self.run_drift(directory, 1, extra=("--plan", "absent.json")), 2
            )
            self.assertFalse((directory / "report.json").exists())

    def test_missing_plan_and_colliding_output_leave_inputs_intact(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.assertEqual(self.run_drift(directory, 0), 2)
            self.assertFalse((directory / "report.json").exists())
            data = observed_plan()
            self.assertEqual(
                self.run_drift(
                    directory, 2, data, ("--output", str(directory / "plan.json"))
                ),
                2,
            )
            self.assertEqual(json.loads((directory / "plan.json").read_text()), data)


@unittest.skipUnless(shutil.which("tofu"), "OpenTofu required for local plan contracts")
class OpenTofuDriftTests(unittest.TestCase):
    def test_actual_clean_output_only_and_error_plans(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "main.tf"
            source.write_text('terraform { required_version = ">= 1.6.0" }\n')

            def tofu(*args):
                return subprocess.run(
                    ["tofu", f"-chdir={directory}", *args],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

            self.assertEqual(tofu("init", "-input=false").returncode, 0)
            for expected_code, expected_status, addition in (
                (0, "no_changes", ""),
                (
                    2,
                    "changes_detected",
                    '\noutput "secret" { value = "DO_NOT_PUBLISH" }\n',
                ),
                (1, "plan_error", '\nvariable "required" { type = string }\n'),
            ):
                with self.subTest(code=expected_code):
                    source.write_text(source.read_text() + addition)
                    result = tofu(
                        "plan", "-input=false", "-detailed-exitcode", "-out=plan.bin"
                    )
                    self.assertEqual(result.returncode, expected_code)
                    data = None
                    if result.returncode != 1:
                        shown = tofu("show", "-json", "plan.bin")
                        self.assertEqual(shown.returncode, 0)
                        data = json.loads(shown.stdout)
                    report = drift_report(config(), result.returncode, data)
                    self.assertEqual(report["status"], expected_status)
                    self.assertNotIn("DO_NOT_PUBLISH", json.dumps(report))
                    if expected_code == 2:
                        self.assertEqual(report["changed_outputs"], 1)
                        self.assertEqual(report["drift"]["resources"], [])


if __name__ == "__main__":
    unittest.main()
