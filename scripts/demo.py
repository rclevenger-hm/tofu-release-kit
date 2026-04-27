"""Exercise policy and deployment outcomes using synthetic plans and localhost."""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tofu_release_kit.config import load_config
from tofu_release_kit.io import write_json, write_text
from tofu_release_kit.plan import summarize
from tofu_release_kit.policy import evaluate
from tofu_release_kit.report import deployment_report, markdown
from tofu_release_kit.verification import verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", choices=["healthy", "blocked", "unhealthy"], default="healthy"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".artifacts" / "demo")
    args = parser.parse_args()
    config = load_config(ROOT / "examples/demo/release-kit.toml")
    plan = json.loads(
        (
            ROOT
            / "tests/fixtures"
            / (
                "protected-delete.json"
                if args.scenario == "blocked"
                else "safe-plan.json"
            )
        ).read_text()
    )
    decision = evaluate(plan, config)
    checks = None
    apply_status = "not_run"
    if decision["allowed"]:

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "revision": "old"
                            if args.scenario == "unhealthy"
                            else "demo-revision"
                        }
                    ).encode()
                )

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                outputs = {
                    "health_url": {
                        "sensitive": False,
                        "value": f"http://127.0.0.1:{server.server_port}/health",
                    },
                    "application_revision": {
                        "sensitive": False,
                        "value": "demo-revision",
                    },
                }
                checks = verify(config, outputs)
                apply_status = "succeeded"  # Simulated apply, explicitly labeled below.
            finally:
                server.shutdown()
                thread.join()
    report = deployment_report(config, summarize(plan), decision, apply_status, checks)
    report["simulation"] = True
    write_json(args.output_dir / f"{args.scenario}.json", report)
    write_text(
        args.output_dir / f"{args.scenario}.md",
        "**LOCAL SIMULATION — no cloud infrastructure was deployed.**\n\n"
        + markdown(report),
    )
    expected = {
        "healthy": "verified",
        "blocked": "blocked",
        "unhealthy": "verification_failed",
    }[args.scenario]
    print(f"Simulated {args.scenario}: {report['status']}")
    return 0 if report["status"] == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
