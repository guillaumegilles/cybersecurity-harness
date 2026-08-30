"""Response-action proposal generation (T040, FR-016). Proposals only — the
harness has no execution capability for any of these actions."""

from __future__ import annotations

from harness.storage.models import AffectedEntity, EvidenceItem, Hypothesis, ResponseActionProposal
from harness.storage.repositories import CaseScopedRepository


def generate_proposals(repo: CaseScopedRepository) -> list[ResponseActionProposal]:
    proposals: list[ResponseActionProposal] = []
    hypotheses = repo.list(Hypothesis)
    entities = repo.list(AffectedEntity)
    evidence_ids = [e.id for e in repo.list(EvidenceItem)
                    if e.trust_classification == "direct_observation"]

    supported = [h for h in hypotheses if h.evaluation == "supported"]
    if not supported:
        return proposals

    endpoints = [e.identifier for e in entities if e.entity_type == "endpoint"]
    users = [e.identifier for e in entities if e.entity_type == "user"]

    if endpoints:
        p = ResponseActionProposal(
            case_id=repo.ctx.case_id,
            action_description=(
                f"PROPOSAL (not executed): consider isolating endpoint(s) {', '.join(endpoints)} "
                "pending confirmation of malicious activity"
            ),
            affected_resources=endpoints,
            evidence_ids=evidence_ids,
            expected_impact="Endpoint users lose network access until released",
            risk="Business disruption if activity is benign",
            rollback_method="Release endpoint from isolation via EDR console",
        )
        repo.add(p)
        proposals.append(p)
    if users:
        p = ResponseActionProposal(
            case_id=repo.ctx.case_id,
            action_description=(
                f"PROPOSAL (not executed): consider credential reset for user(s) {', '.join(users)} "
                "if compromise is confirmed"
            ),
            affected_resources=users,
            evidence_ids=evidence_ids,
            expected_impact="Users must re-authenticate; sessions invalidated",
            risk="User productivity impact if account is not compromised",
            rollback_method="No rollback needed; standard credential lifecycle",
        )
        repo.add(p)
        proposals.append(p)
    repo.session.flush()
    return proposals
