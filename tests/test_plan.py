import json
import unittest

from helpers import plan

from tofu_release_kit.io import KitError
from tofu_release_kit.plan import summarize


class PlanTests(unittest.TestCase):
    def test_both_replacement_orders(self):
        for actions in (["create", "delete"], ["delete", "create"]):
            with self.subTest(actions=actions):
                self.assertEqual(summarize(plan(actions))["counts"], {"replace": 1})

    def test_report_never_contains_resource_values(self):
        text = json.dumps(summarize(plan()))
        self.assertNotIn("DO_NOT_PUBLISH", text)
        self.assertNotIn("platform", text)

    def test_state_document_rejected(self):
        with self.assertRaises(KitError):
            summarize({"format_version": "1.0", "values": {}})

    def test_unsupported_actions_rejected(self):
        for actions in (["future-operation"], [], [{"bad": "value"}]):
            with self.subTest(actions=actions), self.assertRaises(KitError):
                data = plan()
                data["resource_changes"][0]["change"]["actions"] = actions
                summarize(data)

    def test_incomplete_and_errored_plans_rejected(self):
        for flag in (
            {"complete": False},
            {"errored": True},
            {"deferred_changes": [{}]},
        ):
            with self.subTest(flag=flag), self.assertRaises(KitError):
                summarize({**plan(), **flag})

    def test_duplicate_addresses_rejected(self):
        data = plan()
        data["resource_changes"] *= 2
        with self.assertRaises(KitError):
            summarize(data)

    def test_empty_plan_valid(self):
        self.assertEqual(
            summarize({"format_version": "1.2", "planned_values": {}})["resources"], []
        )

    def test_missing_after_rejected(self):
        data = plan()
        data["resource_changes"][0]["change"].pop("after")
        with self.assertRaises(KitError):
            summarize(data)
