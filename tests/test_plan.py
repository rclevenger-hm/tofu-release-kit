import copy
import json
import unittest

from helpers import plan, recovery_plan

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

    def test_current_and_deposed_objects_share_an_address(self):
        result = summarize(recovery_plan())
        self.assertEqual(result["counts"], {"delete": 1, "unchanged": 1})
        self.assertEqual(
            result["resources"],
            [
                {
                    "address": "aws_dynamodb_table.orders",
                    "type": "aws_dynamodb_table",
                    "action": "delete",
                    "deposed": "deadbeef",
                }
            ],
        )
        self.assertNotIn("DO_NOT_PUBLISH", json.dumps(result))

    def test_multiple_deposed_objects_are_distinct_and_sorted(self):
        data = recovery_plan()
        data["resource_changes"][0]["change"]["actions"] = ["update"]
        other = copy.deepcopy(data["resource_changes"][1])
        # Deposed keys are opaque, not a fixed-length hexadecimal contract.
        other["deposed"] = "another-object"
        data["resource_changes"].append(other)
        expected = summarize(data)
        data["resource_changes"].reverse()
        self.assertEqual(summarize(data), expected)
        self.assertEqual(expected["counts"], {"delete": 2, "update": 1})
        self.assertEqual(
            [r.get("deposed") for r in expected["resources"]],
            [None, "another-object", "deadbeef"],
        )

    def test_duplicate_deposed_object_rejected(self):
        data = recovery_plan()
        data["resource_changes"].append(copy.deepcopy(data["resource_changes"][1]))
        with self.assertRaises(KitError):
            summarize(data)

    def test_deposed_key_may_be_reused_at_another_address(self):
        data = recovery_plan()
        other = copy.deepcopy(data["resource_changes"][1])
        other["address"] = "aws_dynamodb_table.other"
        data["resource_changes"].append(other)
        self.assertEqual(summarize(data)["counts"], {"delete": 2, "unchanged": 1})

    def test_malformed_deposed_metadata_rejected(self):
        for value in (None, "", 0, True, [], {}, "x" * 1025):
            with self.subTest(value=value), self.assertRaises(KitError):
                data = recovery_plan()
                data["resource_changes"][1]["deposed"] = value
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
