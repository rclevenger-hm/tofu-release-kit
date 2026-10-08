from tofu_release_kit.config import validate_config


def config():
    return validate_config(
        {
            "schema_version": 1,
            "stack": "orders",
            "environment": "test",
            "policies": {"protected_resources": ["aws_dynamodb_table.orders"]},
            "verification": [
                {
                    "name": "health",
                    "url_from_output": "health_url",
                    "revision_from_output": "revision",
                    "allow_http": True,
                    "timeout_seconds": 0.4,
                    "request_timeout_seconds": 0.2,
                    "interval_seconds": 0.02,
                }
            ],
        }
    )


def plan(actions=None):
    return {
        "format_version": "1.2",
        "planned_values": {},
        "resource_changes": [
            {
                "address": "aws_dynamodb_table.orders",
                "type": "aws_dynamodb_table",
                "mode": "managed",
                "change": {
                    "actions": actions or ["create"],
                    "before": None,
                    "after": {
                        "tags": {"owner": "platform", "environment": "test"},
                        "secret": "DO_NOT_PUBLISH_THIS_SECRET",
                    },
                    "after_unknown": {},
                },
            }
        ],
    }


def outputs(url, revision="expected"):
    return {
        "health_url": {"sensitive": False, "value": url},
        "revision": {"sensitive": False, "value": revision},
    }
