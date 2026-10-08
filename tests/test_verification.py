import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from helpers import config, outputs

from tofu_release_kit.io import KitError
from tofu_release_kit.verification import target_url, verify


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/slow":
            time.sleep(1)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/healthy")
            self.end_headers()
            return
        self.send_response(503 if self.path == "/unhealthy" else 200)
        self.end_headers()
        body = json.dumps(
            {"revision": "old" if self.path == "/old" else "expected"}
        ).encode()
        if self.path == "/invalid":
            body = b"not json"
        if self.path == "/large":
            body = b"x" * 70000
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass


class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_expected_revision_passes(self):
        self.assertTrue(verify(config(), outputs(self.base + "/healthy"))["passed"])

    def test_wrong_revision_fails(self):
        result = verify(config(), outputs(self.base + "/old"))
        self.assertFalse(result["passed"])
        self.assertEqual(result["checks"][0]["reason"], "revision_mismatch")

    def test_unhealthy_invalid_large_and_redirect_fail(self):
        for path, reason in [
            ("unhealthy", "status_mismatch"),
            ("invalid", "invalid_json"),
            ("large", "response_too_large"),
            ("redirect", "status_mismatch"),
        ]:
            with self.subTest(path=path):
                result = verify(config(), outputs(self.base + "/" + path))
                self.assertFalse(result["passed"])
                self.assertEqual(result["checks"][0]["reason"], reason)

    def test_slow_endpoint_has_overall_deadline(self):
        start = time.monotonic()
        result = verify(config(), outputs(self.base + "/slow"))
        self.assertFalse(result["passed"])
        self.assertLess(time.monotonic() - start, 1.0)

    def test_sensitive_output_rejected(self):
        data = outputs(self.base)
        data["health_url"]["sensitive"] = True
        with self.assertRaises(KitError):
            verify(config(), data)

    def test_missing_revision_output_rejected(self):
        data = outputs(self.base)
        del data["revision"]
        with self.assertRaises(KitError):
            verify(config(), data)

    def test_unsafe_urls_rejected(self):
        for url in [
            "http://example.com",
            "file:///etc/passwd",
            "https://user:pass@example.com",
            "https://example.com?token=secret",
            "https://example.com:0/",
            "https://exa\nmple.com",
        ]:
            with self.subTest(url=url), self.assertRaises(KitError):
                target_url(url)

    def test_reports_do_not_include_urls_or_revision_values(self):
        result = json.dumps(verify(config(), outputs(self.base + "/healthy")))
        self.assertNotIn("127.0.0.1", result)
        self.assertNotIn("expected", result)
