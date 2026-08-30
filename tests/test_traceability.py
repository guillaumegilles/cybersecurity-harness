"""Traceability check (T066, Constitution I): every FR maps to >=1 test.

The matrix below is maintained alongside the spec; this test fails if any FR
lacks a mapped, existing test node.
"""

from __future__ import annotations

from pathlib import Path

TESTS = Path(__file__).parent

TRACEABILITY: dict[str, list[str]] = {
    "FR-001": ["contract/test_cases_api.py", "integration/test_investigation_flow.py"],
    "FR-002": ["contract/test_cases_api.py"],
    "FR-003": ["unit/test_repositories.py", "adversarial/test_case_isolation.py"],
    "FR-004": ["unit/test_machine.py", "integration/test_investigation_flow.py"],
    "FR-005": ["adversarial/test_malformed_inputs.py"],
    "FR-005a": ["integration/test_cancellation.py"],
    "FR-006": ["integration/test_investigation_flow.py"],
    "FR-007": ["integration/test_investigation_flow.py", "contract/test_report_schema.py"],
    "FR-008": ["integration/test_provenance.py"],
    "FR-009": ["integration/test_provenance.py", "contract/test_report_schema.py"],
    "FR-010": ["integration/test_provenance.py", "adversarial/test_malformed_inputs.py"],
    "FR-011": ["integration/test_investigation_flow.py", "adversarial/test_malformed_inputs.py"],
    "FR-012": ["contract/test_provenance_api.py", "integration/test_provenance.py"],
    "FR-013": ["contract/test_report_schema.py"],
    "FR-014": ["integration/test_investigation_flow.py"],
    "FR-015": ["integration/test_hypotheses.py"],
    "FR-016": ["integration/test_response_proposals.py"],
    "FR-017": ["unit/test_policy.py", "unit/test_readonly_enforcement.py"],
    "FR-018": ["unit/test_policy.py"],
    "FR-019": ["unit/test_policy.py", "unit/test_readonly_enforcement.py",
               "contract/test_cases_api.py"],
    "FR-020": ["unit/test_fail_safe.py"],
    "FR-021": ["adversarial/test_privilege_escalation.py"],
    "FR-022": ["unit/test_policy.py", "integration/test_audit_completeness.py"],
    "FR-023": ["unit/test_policy.py"],
    "FR-024": ["integration/test_budget_exhaustion.py"],
    "FR-025": ["adversarial/test_prompt_injection.py"],
    "FR-026": ["adversarial/test_prompt_injection.py", "adversarial/test_malformed_inputs.py"],
    "FR-027": ["unit/test_instruction_detector.py", "adversarial/test_prompt_injection.py"],
    "FR-028": ["integration/test_audit_completeness.py"],
    "FR-029": ["integration/test_audit_completeness.py"],
    "FR-030": ["unit/test_audit_chain.py", "adversarial/test_audit_tamper.py"],
    "FR-031": ["unit/test_budget.py"],
    "FR-032": ["integration/test_budget_exhaustion.py"],
    "FR-033": ["unit/test_fail_safe.py", "adversarial/test_malformed_inputs.py"],
    "FR-034": ["contract/test_feedback_api.py", "integration/test_feedback.py"],
    "FR-035": ["adversarial/test_secret_extraction.py"],
}


def test_every_fr_has_mapped_tests():
    missing = {fr: files for fr, files in TRACEABILITY.items() if not files}
    assert not missing


def test_all_mapped_test_files_exist():
    for fr, files in TRACEABILITY.items():
        for f in files:
            assert (TESTS / f).exists(), f"{fr} maps to missing test file {f}"


def test_all_frs_covered():
    expected = {f"FR-{i:03d}" for i in range(1, 36)} | {"FR-005a"}
    assert set(TRACEABILITY) == expected
