"""Output verifier (T029, FR-035): secret scan + claim-evidence completeness."""

from __future__ import annotations

import json

from harness.config.logging import SECRET_VALUE_PATTERN
from harness.storage.repositories import CaseScopedRepository
from harness.storage import models as m


class VerificationFailure(Exception):
    pass


def verify_report(content: dict, repo: CaseScopedRepository) -> list[str]:
    """Return list of verification problems (empty = pass)."""
    problems: list[str] = []

    # 1. Secret scan on the serialized report (FR-035 / SC-005).
    blob = json.dumps(content, default=str)
    if SECRET_VALUE_PATTERN.search(blob):
        problems.append("secret-like value detected in report output")

    # 2. Claim-evidence completeness (FR-007): every material supported claim
    #    must have >=1 supporting evidence link.
    for finding in content.get("findings", []):
        if finding["support_status"] == "supported" and not finding["supporting_evidence_ids"]:
            problems.append(
                f"material claim '{finding['statement'][:80]}' marked supported without evidence"
            )

    # 3. Proposals must be proposal-only.
    for p in content.get("response_action_proposals", []):
        if not p.get("proposal_only", True):
            problems.append("response action proposal not marked proposal_only")

    return problems
