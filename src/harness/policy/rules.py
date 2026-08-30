"""Prohibited-operation policy rules (T039, FR-017).

Explicit deny list plus default deny for any non-registered operation.
"""

from __future__ import annotations

# Operation-name prefixes/classes that are always denied (FR-017).
PROHIBITED_OPERATIONS = frozenset(
    {
        "isolate_endpoint",
        "disable_account",
        "suspend_account",
        "modify_account",
        "revoke_session",
        "revoke_credentials",
        "delete_message",
        "quarantine_message",
        "block_ip",
        "block_domain",
        "block_file",
        "block_process",
        "modify_detection_rule",
        "change_security_policy",
        "create_firewall_rule",
        "execute_command",
        "run_shell",
        "upload_external",
        "exfiltrate",
        "request_secret",
        "expose_secret",
        "modify_audit",
        "delete_audit",
        "suppress_audit",
        "install_tool",
        "install_extension",
        "install_connector",
        "install_skill",
        "register_tool",
        "create_subagent",
        "spawn_agent",
        "write_memory",
    }
)

DENY_REASON_PROHIBITED = "operation_prohibited_readonly_policy"
DENY_REASON_UNREGISTERED = "operation_not_registered"
DENY_REASON_UNAUTHORIZED_SOURCE = "not_authorized"  # never reveals resource existence (FR-019)
DENY_REASON_BUDGET = "budget_exhausted"
DENY_REASON_AMBIGUOUS = "authorization_context_incomplete"


def is_prohibited(operation: str) -> bool:
    op = operation.lower().strip()
    return op in PROHIBITED_OPERATIONS or any(op.startswith(p + ":") for p in PROHIBITED_OPERATIONS)
