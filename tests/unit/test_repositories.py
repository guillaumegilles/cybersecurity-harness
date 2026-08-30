"""Repository case-isolation tests (T020, FR-003)."""

from __future__ import annotations

import pytest

from harness.orchestrator.case_service import create_case
from harness.storage.models import Claim, EvidenceItem
from harness.storage.repositories import (
    CaseContext,
    CaseIsolationError,
    CaseScopedRepository,
    get_case,
)
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest


def _mkcase(session, analyst="alice"):
    return create_case(
        session, analyst,
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )


def _repo(session, case):
    return CaseScopedRepository(
        session, CaseContext(case.id, case.analyst_id, case.agent_execution_id)
    )


def test_cross_case_write_rejected(session):
    a, b = _mkcase(session), _mkcase(session)
    repo_a = _repo(session, a)
    with pytest.raises(CaseIsolationError):
        repo_a.add(EvidenceItem(case_id=b.id, source="x", trust_classification="direct_observation"))


def test_cross_case_read_impossible(session):
    a, b = _mkcase(session), _mkcase(session)
    repo_a, repo_b = _repo(session, a), _repo(session, b)
    repo_a.add(EvidenceItem(case_id=a.id, source="alert_source",
                            trust_classification="direct_observation", content={"k": "v"}))
    session.flush()
    assert len(repo_a.list(EvidenceItem)) == 1
    assert len(repo_b.list(EvidenceItem)) == 0


def test_get_scoped_by_case(session):
    a, b = _mkcase(session), _mkcase(session)
    repo_a, repo_b = _repo(session, a), _repo(session, b)
    claim = Claim(case_id=a.id, statement="s", claim_type="direct_observation",
                  support_status="supported", confidence="high")
    repo_a.add(claim)
    session.flush()
    assert repo_a.get(Claim, claim.id) is not None
    assert repo_b.get(Claim, claim.id) is None


def test_case_access_policy(session):
    a = _mkcase(session, analyst="alice")
    session.commit()
    assert get_case(session, a.id, "alice") is not None
    # Other analyst: indistinguishable from nonexistent (FR-019)
    assert get_case(session, a.id, "bob") is None
    assert get_case(session, "no-such-case", "alice") is None
