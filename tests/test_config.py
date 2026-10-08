import unittest

from helpers import config

from tofu_release_kit.config import validate_config
from tofu_release_kit.io import KitError


class ConfigurationTests(unittest.TestCase):
    def test_valid_config_roundtrip(self):
        self.assertEqual(validate_config(config()), config())

    def test_unknown_field_rejected(self):
        data = config()
        data["polcies"] = {}
        with self.assertRaises(KitError):
            validate_config(data)

    def test_invalid_versions_rejected(self):
        for version in [True, "1", 2, None]:
            with self.subTest(version=version), self.assertRaises(KitError):
                validate_config({**config(), "schema_version": version})

    def test_verification_cannot_be_empty(self):
        with self.assertRaises(KitError):
            validate_config({**config(), "verification": []})

    def test_bad_timeouts_rejected(self):
        for value in [-1, 0, float("nan"), float("inf"), True, "5", 601]:
            data = config()
            data["verification"][0]["timeout_seconds"] = value
            with self.subTest(value=value), self.assertRaises(KitError):
                validate_config(data)

    def test_duplicate_checks_rejected(self):
        data = config()
        data["verification"] *= 2
        with self.assertRaises(KitError):
            validate_config(data)

    def test_unsafe_identifiers_rejected(self):
        with self.assertRaises(KitError):
            validate_config({**config(), "stack": "../../bad"})

    def test_unknown_check_field_rejected(self):
        data = config()
        data["verification"][0]["expected_stats"] = 200
        with self.assertRaises(KitError):
            validate_config(data)
