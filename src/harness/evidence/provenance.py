"""Provenance query service (T034, FR-012)."""

from __future__ import annotations

from typing import Any

from harness.storage import models as m
from harness.storage.repositories import CaseScopedRepository


def claim_evidence(repo: CaseScopedRepository, claim_id: str) -> dict[str, Any] | None:
    claim = repo.get(m.Claim, claim_id)
    if claim is None:
        return None

    links = repo.get_claim_evidence_links(claim_id)
    evidence_entries: list[dict[str, Any]] = []
    for link in links:
        item = repo.get(m.EvidenceItem, link.evidence_id)
        if item is None:
            continue
        evidence_entries.append(
            {
                "id": item.id,
                "relationship": link.relationship,
                "source": item.source,
                "source_record_id": item.source_record_id,
                "collected_at": item.collected_at.isoformat(),
                "event_at": item.event_at.isoformat() if item.event_at else None,
                "trust_classification": item.trust_classification,
                "content": item.content,
            }
        )

    missing = None
    if claim.support_status in ("inconclusive", "unsupported"):
        missing = "Evidence is insufficient to conclusively support this claim"
    elif not evidence_entries:
        missing = "No evidence links recorded for this claim"

    return {
        "claim": {
            "id": claim.id,
            "statement": claim.statement,
            "claim_type": claim.claim_type,
            "support_status": claim.support_status,
            "confidence": claim.confidence,
        },
        "evidence": evidence_entries,
        "missing_evidence": missing,
    }
