import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tofu_release_kit.binding import bind, check_binding
from tofu_release_kit.io import KitError


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "input"
        self.path.write_text("original")
        self.now = datetime(2026, 10, 8, tzinfo=UTC)

    def manifest(self, **kwargs):
        return bind(
            self.path,
            self.path,
            self.path,
            "a" * 40,
            "test",
            "1.13.1",
            now=self.now,
            **kwargs,
        )

    def test_valid_binding(self):
        self.assertTrue(
            check_binding(self.manifest(), self.manifest(), now=self.now)["valid"]
        )

    def test_modified_plan_rejected(self):
        old = self.manifest()
        self.path.write_text("tampered")
        with self.assertRaises(KitError):
            check_binding(old, self.manifest(), now=self.now)

    def test_changed_commit_environment_and_version_rejected(self):
        for field, value in [
            ("commit", "b" * 40),
            ("environment", "production"),
            ("tofu_version", "1.12.0"),
        ]:
            data = self.manifest()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(KitError):
                check_binding(data, self.manifest(), now=self.now)

    def test_expiry_and_future_rejected(self):
        for delta in [timedelta(hours=2), timedelta(seconds=-1)]:
            with self.subTest(delta=delta), self.assertRaises(KitError):
                check_binding(self.manifest(), self.manifest(), now=self.now + delta)

    def test_naive_timestamp_rejected(self):
        data = self.manifest()
        data["created_at"] = "2026-10-08T00:00:00"
        with self.assertRaises(KitError):
            check_binding(data, self.manifest(), now=self.now)
