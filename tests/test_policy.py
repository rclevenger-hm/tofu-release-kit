import json
import shutil
import subprocess
import unittest
from unittest.mock import patch

from helpers import config, plan

from tofu_release_kit.io import KitError
from tofu_release_kit.policy import evaluate


class PolicyFailureTests(unittest.TestCase):
    def test_missing_executable_fails_closed(self):
        with self.assertRaises(KitError):
            evaluate(plan(), config(), "/missing/opa")

    @patch("tofu_release_kit.policy.subprocess.run")
    def test_undefined_decision_fails_closed(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "{}", "")
        with self.assertRaises(KitError):
            evaluate(plan(), config())

    @patch("tofu_release_kit.policy.subprocess.run")
    def test_inconsistent_decision_fails_closed(self, run):
        value = {
            "allowed": True,
            "findings": [{"rule": "x", "address": "a", "reason": "bad"}],
        }
        run.return_value = subprocess.CompletedProcess(
            [], 0, json.dumps({"result": [{"expressions": [{"value": value}]}]}), ""
        )
        with self.assertRaises(KitError):
            evaluate(plan(), config())


@unittest.skipUnless(shutil.which("opa"), "OPA not installed; CI requires and runs OPA")
class LivePolicyTests(unittest.TestCase):
    def test_good_plan_passes(self):
        self.assertTrue(evaluate(plan(), config())["allowed"])

    def test_protected_replacement_blocked(self):
        decision = evaluate(plan(["create", "delete"]), config())
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["findings"][0]["rule"], "protected-resource")

    def test_unknown_tags_blocked(self):
        data = plan()
        data["resource_changes"][0]["change"]["after_unknown"] = {"tags": True}
        self.assertFalse(evaluate(data, config())["allowed"])
