"""Cancellation tests (T056, FR-005a / clarification Q1).

The dev/eval API runs investigations synchronously, so mid-run cancellation
is exercised at the orchestrator level with the cooperative cancel flag.
"""

from __future__ import annotations

from harness.orchestrator import states
from harness.orchestrator.case_service import create_case
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest

ALL = ("alert_source", "endpoint_telemetry", "identity_context")


def test_cancel_mid_run_produces_partial_report(session):
    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source,
                                           alert_id="ALERT-1001")),
    )
    session.commit()
    states.request_cancel(case.id)  # cancel requested before/while running
    case = states.run_investigation(session, case, ALL)
    assert case.status == "cancelled"
    assert case.workflow_state == "CANCELLED"
    assert "cancelled" in case.termination_reason

    from sqlalchemy import select
    from harness.storage.models import InvestigationReport
    report = session.scalars(
        select(InvestigationReport).where(InvestigationReport.case_id == case.id)
    ).first()
    assert report is not None
    assert report.report_kind == "partial"


def test_cancel_endpoint_on_running_case_api(client, headers):
    # API investigations run synchronously; cancel on terminal case gives 409.
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    r2 = client.post(f"/cases/{case_id}/cancel", headers=headers)
    assert r2.status_code == 409  # already terminal
