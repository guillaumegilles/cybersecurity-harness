"""CLI entry points (T031): issue-token, investigate."""

from __future__ import annotations

import argparse
import json
import sys

from harness.api.identity import get_identity_provider
from harness.config.logging import configure_logging
from harness.orchestrator import states
from harness.orchestrator.case_service import create_case
from harness.storage.db import get_session, init_db
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest


def cmd_issue_token(args: argparse.Namespace) -> int:
    provider = get_identity_provider()
    token = provider.issue(args.analyst, args.sources.split(",") if args.sources else [])
    print(token)
    return 0


def cmd_investigate(args: argparse.Namespace) -> int:
    configure_logging()
    init_db()
    session = get_session()
    overrides = {}
    if args.max_tool_operations:
        overrides["max_tool_operations"] = args.max_tool_operations
    if args.max_elapsed_seconds:
        overrides["max_elapsed_seconds"] = args.max_elapsed_seconds
    req = CreateCaseRequest(
        alert=AlertInput(origin=AlertOrigin.connected_source, alert_id=args.alert_id),
        limit_overrides=overrides or None,
    )
    case = create_case(session, args.analyst, req)
    session.commit()
    sources = tuple((args.sources or "alert_source,endpoint_telemetry,identity_context").split(","))
    case = states.run_investigation(session, case, sources)
    print(json.dumps({
        "case_id": case.id,
        "status": case.status,
        "workflow_state": case.workflow_state,
        "termination_reason": case.termination_reason,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_token = sub.add_parser("issue-token", help="Issue a dev analyst token")
    p_token.add_argument("--analyst", required=True)
    p_token.add_argument("--sources", default="")
    p_token.set_defaults(func=cmd_issue_token)

    p_inv = sub.add_parser("investigate", help="Run an investigation locally")
    p_inv.add_argument("--alert-id", required=True)
    p_inv.add_argument("--analyst", required=True)
    p_inv.add_argument("--sources", default=None)
    p_inv.add_argument("--max-tool-operations", type=int, default=None)
    p_inv.add_argument("--max-elapsed-seconds", type=int, default=None)
    p_inv.set_defaults(func=cmd_investigate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
