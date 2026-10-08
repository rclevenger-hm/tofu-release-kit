import json
import unittest

from helpers import config, plan

from tofu_release_kit.io import KitError
from tofu_release_kit.plan import summarize
from tofu_release_kit.report import deployment_report, markdown


class ReportTests(unittest.TestCase):
    def test_verification_extra_fields_are_not_published(self):
        checks = self.report("succeeded", True)["verification"]
        checks["secret"] = "private-value"
        checks["checks"][0]["body"] = "private-value"
        result = deployment_report(
            config(),
            summarize(plan()),
            {"allowed": True, "findings": []},
            "succeeded",
            checks,
        )
        self.assertNotIn("private-value", json.dumps(result))

    def report(self, apply="not_run", passed=None, allowed=True):
        checks = (
            None
            if passed is None
            else {
                "stack": "orders",
                "environment": "test",
                "passed": passed,
                "checks": [
                    {
                        "name": "health",
                        "passed": passed,
                        "reason": "verified" if passed else "revision_mismatch",
                        "attempts": 1,
                    }
                ],
            }
        )
        return deployment_report(
            config(),
            summarize(plan()),
            {"allowed": allowed, "findings": []},
            apply,
            checks,
        )

    def test_status_transitions(self):
        for apply, passed, allowed, expected in [
            ("not_run", None, False, "blocked"),
            ("not_run", None, True, "reviewed"),
            ("failed", None, True, "apply_failed"),
            ("succeeded", None, True, "unverified"),
            ("succeeded", False, True, "verification_failed"),
            ("succeeded", True, True, "verified"),
        ]:
            with self.subTest(expected=expected):
                self.assertEqual(
                    self.report(apply, passed, allowed)["status"], expected
                )

    def test_markdown_escapes_resource_addresses(self):
        report = self.report()
        report["plan"]["resources"][0]["address"] = "<script>|\n`bad`"
        result = markdown(report)
        self.assertNotIn("<script>", result)
        self.assertIn("&#124;", result)

    def test_foreign_environment_verification_rejected(self):
        checks = self.report("succeeded", True)["verification"]
        checks["environment"] = "production"
        with self.assertRaises(KitError):
            deployment_report(
                config(),
                summarize(plan()),
                {"allowed": True, "findings": []},
                "succeeded",
                checks,
            )

    def test_incomplete_verification_rejected(self):
        checks = {
            "stack": "orders",
            "environment": "test",
            "passed": True,
            "checks": [],
        }
        with self.assertRaises(KitError):
            deployment_report(
                config(),
                summarize(plan()),
                {"allowed": True, "findings": []},
                "succeeded",
                checks,
            )

    def test_no_secret_values_in_report(self):
        self.assertNotIn("DO_NOT_PUBLISH", json.dumps(self.report()))
