import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class ReadinessHandlerTests(unittest.TestCase):
    def handler(self, client):
        boto = types.ModuleType("boto3")
        boto.client = lambda name: client
        botocore = types.ModuleType("botocore.exceptions")
        botocore.BotoCoreError = RuntimeError
        botocore.ClientError = ValueError
        path = (
            Path(__file__).resolve().parents[1]
            / "examples/aws-serverless/app/handler.py"
        )
        spec = importlib.util.spec_from_file_location("example_handler", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"boto3": boto, "botocore.exceptions": botocore}):
            spec.loader.exec_module(module)
        return module.handler

    def test_active_table_exposes_requested_revision(self):
        client = Mock()
        client.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        with patch.dict(os.environ, {"TABLE_NAME": "example", "REVISION": "abc"}):
            response = self.handler(client)({}, None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["revision"], "abc")
        client.describe_table.assert_called_once_with(TableName="example")

    def test_dependency_failure_is_unhealthy_without_exception_details(self):
        client = Mock()
        client.describe_table.side_effect = RuntimeError("private account details")
        with patch.dict(os.environ, {"TABLE_NAME": "example", "REVISION": "abc"}):
            response = self.handler(client)({}, None)
        self.assertEqual(response["statusCode"], 503)
        self.assertNotIn("private", response["body"])
