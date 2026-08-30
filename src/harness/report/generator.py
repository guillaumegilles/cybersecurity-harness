"""Report generation (T029, T058; FR-013, FR-032)."""

from __future__ import annotations

from datetime import datetime, timezone

from harness.audit.service import AuditService
from harness.storage import models as m
from harness.storage.repositories import CaseScopedRepository
from harness.storage.schemas import (
    EntityEntry,
    FindingEntry,
    HypothesisEntry,
    ProposalEntry,
    ReportContent,
    TimelineEntry,
    ToolOperationEntry,
)


def _severity(repo: CaseScopedRepository) -> str:
    hyps = repo.list(m.Hypothesis)
    if any(h.evaluation == "supported" for h in hyps):
        return "high"
    if any(h.evaluation == "inconclusive" for h in hyps):
        return "medium — inconclusive elements remain"
    return "low"


def build_report_content(
    case: m.InvestigationCase,
    repo: CaseScopedRepository,
    limitations: list[str] | None = None,
) -> ReportContent:
    evidence = {e.id: e for e in repo.list(m.EvidenceItem)}
    claims = repo.list(m.Claim)
    findings: list[FindingEntry] = []
    contradicting: list[str] = []
    missing: list[str] = []

    for claim in claims:
        links = repo.get_claim_evidence_links(claim.id)
        supporting = [l.evidence_id for l in links if l.relationship == "supports"]
        contra = [l.evidence_id for l in links if l.relationship == "contradicts"]
        findings.append(
            FindingEntry(
                claim_id=claim.id,
                statement=claim.statement,
                claim_type=claim.claim_type,
                support_status=claim.support_status,
                confidence=claim.confidence,
                supporting_evidence_ids=supporting,
                contradicting_evidence_ids=contra,
            )
        )
        if contra:
            contradicting.append(f"Claim '{claim.statement[:120]}' has contradicting evidence")
        if claim.support_status in ("inconclusive", "unsupported"):
            missing.append(f"Claim '{claim.statement[:120]}' lacks conclusive evidence")

    hyp_entries = [
        HypothesisEntry(
            statement=h.statement,
            evaluation=h.evaluation,
            confirming_evidence_needed=h.confirming_evidence_needed,
            rejecting_evidence_needed=h.rejecting_evidence_needed,
        )
        for h in repo.list(m.Hypothesis)
    ]

    queries = [h.confirming_evidence_needed for h in repo.list(m.Hypothesis)
               if h.evaluation == "inconclusive" and h.confirming_evidence_needed]

    tool_ops = repo.list(m.ToolOperation)
    failed_sources = sorted({op.tool_name.split(".")[0] for op in tool_ops if op.outcome == "failed"})
    lims = list(limitations or [])
    for src in failed_sources:
        lims.append(f"Evidence from source '{src}' was unavailable; findings may be incomplete")
        missing.append(f"Evidence from source '{src}' could not be retrieved")

    manipulated = [e for e in evidence.values() if e.manipulation_flag]
    if manipulated:
        lims.append(
            f"{len(manipulated)} evidence item(s) contained apparent instructions targeting the "
            "agent; content was treated strictly as data and the attempts were recorded"
        )

    return ReportContent(
        case_id=case.id,
        alert_id=case.alert_id,
        status=case.status,
        alert_summary=_alert_summary(case, repo),
        scope=case.scope,
        timeline=[
            TimelineEntry(event_at=t.event_at, description=t.description, evidence_ids=t.evidence_ids)
            for t in sorted(repo.list(m.TimelineEvent), key=lambda t: (t.event_at, t.id))
        ],
        affected_entities=[
            EntityEntry(entity_type=e.entity_type, identifier=e.identifier, evidence_ids=e.evidence_ids)
            for e in repo.list(m.AffectedEntity)
        ],
        findings=findings,
        hypotheses=hyp_entries,
        contradicting_or_inconclusive_evidence=contradicting,
        missing_information=missing,
        severity_assessment=_severity(repo),
        recommended_queries=queries,
        response_action_proposals=[
            ProposalEntry(
                action_description=p.action_description,
                affected_resources=p.affected_resources,
                evidence_ids=p.evidence_ids,
                expected_impact=p.expected_impact,
                risk=p.risk,
                rollback_method=p.rollback_method,
            )
            for p in repo.list(m.ResponseActionProposal)
        ],
        limitations=lims,
        data_sources_consulted=sorted({op.tool_name.split(".")[0] for op in tool_ops
                                       if op.outcome == "success"}),
        tool_operations=[
            ToolOperationEntry(tool_name=op.tool_name, operation=op.operation,
                               outcome=op.outcome, requested_at=op.requested_at)
            for op in tool_ops
        ],
        started_at=case.started_at,
        completed_at=case.completed_at or datetime.now(timezone.utc),
    )


def _alert_summary(case: m.InvestigationCase, repo: CaseScopedRepository) -> str:
    for e in repo.list(m.EvidenceItem):
        if e.source == "alert_source" and "rule_name" in e.content:
            return (f"Alert {case.alert_id}: {e.content.get('rule_name')} "
                    f"(severity {e.content.get('severity', 'unknown')})")
    return f"Alert {case.alert_id} (details unavailable)"


def persist_report(
    case: m.InvestigationCase,
    repo: CaseScopedRepository,
    audit: AuditService,
    report_kind: str,
    limitations: list[str] | None = None,
    verified: bool = False,
) -> m.InvestigationReport:
    content = build_report_content(case, repo, limitations)
    report = m.InvestigationReport(
        case_id=case.id,
        report_kind=report_kind,
        content=content.model_dump(mode="json"),
        verified=verified,
    )
    repo.add(report)
    repo.session.flush()
    audit.append(case.id, "report_generated", actor="report_generator",
                 payload={"report_id": report.id, "kind": report_kind, "verified": verified})
    return report


def render_markdown(content: dict) -> str:
    lines = [
        f"# Investigation Report — Case {content['case_id']}",
        "",
        f"**Alert**: {content['alert_id']}  |  **Status**: {content['status']}",
        f"**Severity**: {content['severity_assessment']}",
        f"**Started**: {content['started_at']}  |  **Completed**: {content['completed_at']}",
        "",
        f"## Summary\n{content['alert_summary']}",
        f"\n## Scope\n{content['scope'] or '(default: single-alert investigation)'}",
        "\n## Timeline",
    ]
    for t in content["timeline"]:
        lines.append(f"- {t['event_at']}: {t['description']}")
    lines.append("\n## Affected Entities")
    for e in content["affected_entities"]:
        lines.append(f"- {e['entity_type']}: `{e['identifier']}`")
    lines.append("\n## Findings")
    for f in content["findings"]:
        lines.append(f"- [{f['claim_type']}/{f['confidence']}] {f['statement']} "
                     f"(evidence: {len(f['supporting_evidence_ids'])})")
    lines.append("\n## Hypotheses")
    for h in content["hypotheses"]:
        lines.append(f"- ({h['evaluation']}) {h['statement']}")
    lines.append("\n## Response Action Proposals (NOT executed)")
    for p in content["response_action_proposals"]:
        lines.append(f"- {p['action_description']}")
    lines.append("\n## Limitations")
    for l in content["limitations"]:
        lines.append(f"- {l}")
    lines.append("\n## Missing Information")
    for msg in content["missing_information"]:
        lines.append(f"- {msg}")
    return "\n".join(lines)
