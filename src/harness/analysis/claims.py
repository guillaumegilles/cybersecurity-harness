"""Claim and hypothesis generation (T027, T061; FR-007, FR-009–FR-011, FR-015).

Model output is untrusted: it is parsed, schema-validated, and every claim it
influences is typed as inference unless deterministically backed by evidence.
"""

from __future__ import annotations

import json

from harness.audit.service import AuditService
from harness.model.gateway import ModelGateway
from harness.model.prompts import SYSTEM_PROMPT, build_user_prompt
from harness.orchestrator.budget import BudgetService
from harness.storage.models import Claim, ClaimEvidenceLink, EvidenceItem, Hypothesis
from harness.storage.repositories import CaseScopedRepository

_VALID_EVAL = {"supported", "rejected", "inconclusive"}
_VALID_CONF = {"high", "medium", "low", "inconclusive"}


def generate_observation_claims(repo: CaseScopedRepository, audit: AuditService) -> list[Claim]:
    """Deterministic direct-observation claims: one per evidence item with a
    source record identifier (no model involvement — these are observed facts)."""
    claims: list[Claim] = []
    for item in repo.list(EvidenceItem):
        if item.trust_classification != "direct_observation" or not item.source_record_id:
            continue
        etype = item.content.get("event_type") or item.content.get("rule_name") or "event"
        claim = Claim(
            case_id=repo.ctx.case_id,
            statement=f"Observed {etype} (source {item.source}, record {item.source_record_id})",
            claim_type="direct_observation",
            support_status="supported",
            confidence="high",
            material=True,
        )
        repo.add(claim)
        repo.session.flush()
        repo.add_claim_evidence_link(
            ClaimEvidenceLink(claim_id=claim.id, evidence_id=item.id, relationship="supports")
        )
        audit.append(repo.ctx.case_id, "claim_generated", actor="claims_service",
                     payload={"claim_id": claim.id, "claim_type": "direct_observation"})
        claims.append(claim)
    repo.session.flush()
    return claims


def generate_hypotheses(
    repo: CaseScopedRepository,
    audit: AuditService,
    budget: BudgetService,
    model: ModelGateway,
    objective: str,
) -> list[Hypothesis]:
    """Model-assisted hypothesis generation. Output is validated and stored as
    inference-type material, never as observed fact (FR-010)."""
    evidence_payload = [
        {
            "source": e.source,
            "source_record_id": e.source_record_id,
            "event_at": str(e.event_at),
            "trust": e.trust_classification,
            "content": e.content,
        }
        for e in repo.list(EvidenceItem)
    ]

    budget.consume_model_call()
    raw = model.complete(SYSTEM_PROMPT, build_user_prompt(objective, evidence_payload))

    hypotheses: list[Hypothesis] = []
    try:
        parsed = json.loads(raw)
        candidates = parsed.get("hypotheses", [])
        if not isinstance(candidates, list):
            raise ValueError("hypotheses not a list")
    except (json.JSONDecodeError, ValueError, AttributeError):
        candidates = []

    for cand in candidates[:10]:
        if not isinstance(cand, dict) or not cand.get("statement"):
            continue
        evaluation = cand.get("evaluation", "inconclusive")
        confidence = cand.get("confidence", "inconclusive")
        # Inconclusive over fabrication: invalid values degrade to inconclusive (FR-011).
        if evaluation not in _VALID_EVAL:
            evaluation = "inconclusive"
        if confidence not in _VALID_CONF:
            confidence = "inconclusive"

        hyp = Hypothesis(
            case_id=repo.ctx.case_id,
            statement=str(cand["statement"])[:2000],
            evaluation=evaluation,
            confirming_evidence_needed=str(cand.get("confirming_evidence_needed", ""))[:2000],
            rejecting_evidence_needed=str(cand.get("rejecting_evidence_needed", ""))[:2000],
        )
        repo.add(hyp)
        repo.session.flush()

        # Each hypothesis yields an inference-type claim linked to all evidence
        # that supports/contradicts per deterministic linkage below.
        claim = Claim(
            case_id=repo.ctx.case_id,
            statement=hyp.statement,
            claim_type="inference",
            support_status="supported" if evaluation == "supported" else "inconclusive",
            confidence=confidence,
            material=True,
        )
        repo.add(claim)
        repo.session.flush()
        hyp.claim_ids = [claim.id]

        # Deterministic linkage: supported hypotheses link to direct-observation evidence.
        if evaluation == "supported":
            linked = False
            for item in repo.list(EvidenceItem):
                if item.trust_classification == "direct_observation":
                    repo.add_claim_evidence_link(
                        ClaimEvidenceLink(claim_id=claim.id, evidence_id=item.id,
                                          relationship="supports")
                    )
                    linked = True
            if not linked:
                # No direct evidence -> cannot present as supported (FR-007/FR-011).
                claim.support_status = "inconclusive"
                hyp.evaluation = "inconclusive"

        audit.append(repo.ctx.case_id, "claim_generated", actor="claims_service",
                     payload={"claim_id": claim.id, "claim_type": "inference",
                              "hypothesis_id": hyp.id})
        hypotheses.append(hyp)

    if not hypotheses:
        # Model returned nothing usable: record an explicit inconclusive hypothesis.
        hyp = Hypothesis(
            case_id=repo.ctx.case_id,
            statement="No hypothesis could be established from available evidence",
            evaluation="inconclusive",
            confirming_evidence_needed="Additional evidence from approved sources",
            rejecting_evidence_needed="",
        )
        repo.add(hyp)
        hypotheses.append(hyp)

    repo.session.flush()
    return hypotheses
