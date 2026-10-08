"""One isolated HTTP request. Its parent process enforces the complete deadline."""

import json
import sys
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check(payload):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        payload["url"],
        headers={"User-Agent": "tofu-release-kit/0.1", "Accept": "application/json"},
    )
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != payload["expected_status"]:
                return "status_mismatch"
            body = response.read(65537)
            if len(body) > 65536:
                return "response_too_large"
            if "expected_revision" in payload:
                try:
                    value = json.loads(body)
                except (ValueError, UnicodeError):
                    return "invalid_json"
                if (
                    not isinstance(value, dict)
                    or value.get(payload["revision_field"])
                    != payload["expected_revision"]
                ):
                    return "revision_mismatch"
            return "verified"
    except urllib.error.HTTPError:
        return "status_mismatch"
    except (OSError, ValueError):
        return "connection_error"


if __name__ == "__main__":
    reason = check(json.load(sys.stdin))
    print(json.dumps({"passed": reason == "verified", "reason": reason}))
