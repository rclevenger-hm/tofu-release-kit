import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingTests(unittest.TestCase):
    def test_lambda_package_is_reproducible(self):
        package = script("package_lambda").package
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            source = path / "handler.py"
            source.write_text("def handler(event, context): return {}\n")
            package(source, path / "one.zip")
            package(source, path / "two.zip")
            self.assertEqual(
                (path / "one.zip").read_bytes(), (path / "two.zip").read_bytes()
            )


@unittest.skipUnless(shutil.which("gpg"), "GnuPG required for artifact-transfer tests")
class ArtifactTests(unittest.TestCase):
    def test_seal_open_and_wrong_key(self):
        transfer = script("plan_artifact").transfer
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "plan.bin").write_bytes(b"private plan bytes")
            (source / "binding.json").write_text('{"schema_version": 1}')
            artifact = root / "sealed.gpg"
            key = "test-key-" + "a" * 48
            transfer("seal", source, artifact, key)
            self.assertNotIn(b"private plan bytes", artifact.read_bytes())
            transfer("open", root / "destination", artifact, key)
            self.assertEqual(
                (root / "destination/plan.bin").read_bytes(), b"private plan bytes"
            )
            with self.assertRaises(ValueError):
                transfer("open", root / "wrong", artifact, "different-key-" + "b" * 48)
            self.assertFalse((root / "wrong/plan.bin").exists())

    def test_short_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            script("plan_artifact").transfer(
                "seal", Path(temp), Path(temp) / "artifact", "short"
            )
