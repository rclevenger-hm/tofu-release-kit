"""Command-line entry points. Exit 0=pass, 1=denied/failed check, 2=input/tool error."""

import argparse
import json
import sys

from . import __version__
from .binding import bind, check_binding
from .config import load_config
from .io import KitError, read_json, write_json, write_text
from .plan import summarize
from .policy import evaluate
from .report import deployment_report, markdown
from .verification import verify


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("inspect", "gate", "verify", "report"):
        command = commands.add_parser(name)
        command.add_argument("--config", required=True)
        command.add_argument("--output", required=True)
        if name in ("inspect", "gate", "report"):
            command.add_argument(
                "--plan", required=True, help="Private saved-plan JSON"
            )
        if name in ("gate", "report"):
            command.add_argument("--opa", default="opa")
        if name == "verify":
            command.add_argument(
                "--outputs", required=True, help="Private tofu output -json file"
            )
        if name == "report":
            command.add_argument(
                "--apply-status",
                choices=["not_run", "succeeded", "failed"],
                default="not_run",
            )
            command.add_argument("--verification")
            command.add_argument("--commit")
            command.add_argument("--markdown")
    for name in ("bind", "check-binding"):
        command = commands.add_parser(name)
        for field in (
            "plan",
            "lockfile",
            "config",
            "commit",
            "environment",
            "tofu-version",
            "output",
        ):
            command.add_argument("--" + field, required=True)
        command.add_argument(
            "--context", help="Optional private backend/account context file to bind"
        )
        if name == "check-binding":
            command.add_argument("--manifest", required=True)
            command.add_argument("--max-age-seconds", type=int, default=3600)
    return root


def run(args):
    if args.command in ("bind", "check-binding"):
        config = load_config(args.config)
        if config["environment"] != args.environment:
            raise KitError("Binding environment must match configuration")
        result = bind(
            args.plan,
            args.lockfile,
            args.config,
            args.commit,
            args.environment,
            args.tofu_version,
            context=args.context,
        )
        if args.command == "check-binding":
            if not 1 <= args.max_age_seconds <= 86400:
                raise KitError("max-age-seconds must be between 1 and 86400")
            result = check_binding(
                read_json(args.manifest), result, args.max_age_seconds
            )
        code = 0
    else:
        config = load_config(args.config)
        if args.command == "verify":
            result = verify(config, read_json(args.outputs))
            code = 0 if result["passed"] else 1
        else:
            plan = read_json(args.plan)
            summary = summarize(plan)
            if args.command == "inspect":
                result, code = summary, 0
            else:
                decision = evaluate(plan, config, args.opa)
                result, code = decision, 0 if decision["allowed"] else 1
                if args.command == "report":
                    checks = read_json(args.verification) if args.verification else None
                    result = deployment_report(
                        config,
                        summary,
                        decision,
                        args.apply_status,
                        checks,
                        args.commit,
                    )
                    code = 0 if result["status"] in {"reviewed", "verified"} else 1
                    if args.markdown:
                        write_text(args.markdown, markdown(result))
    write_json(args.output, result)
    print(json.dumps({"command": args.command, "exit_code": code}))
    return code


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (KitError, OSError) as exc:
        # OS messages may contain paths/inputs. Keep errors safe for public CI logs.
        message = str(exc) if isinstance(exc, KitError) else "File operation failed"
        print(f"error: {message}", file=sys.stderr)
        return 2
