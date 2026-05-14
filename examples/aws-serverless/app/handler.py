"""Minimal read-only readiness API. No client data is accepted or stored."""

import json
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

client = boto3.client("dynamodb")


def handler(event, context):
    try:
        table = client.describe_table(TableName=os.environ["TABLE_NAME"])
        ready = table["Table"]["TableStatus"] == "ACTIVE"
    except (BotoCoreError, ClientError, KeyError):
        ready = False
    return {"statusCode": 200 if ready else 503,
            "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps({"ready": ready, "revision": os.environ.get("REVISION", "unknown")})}
