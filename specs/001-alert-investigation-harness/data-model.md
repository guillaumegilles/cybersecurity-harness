# Data Model: Read-Only Alert Investigation Harness

**Date**: 2026-08-28 | **Plan**: [plan.md](./plan.md)

All entities carry `created_at`. Every case-scoped entity carries `case_id` and is only reachable through case-filtered repositories (see research R12).

## Entities

### InvestigationCase

| Field | Type | Notes |
|---|---|---|
| id | UUID | Unique case identifier (FR-002) |
| alert_id | string | Identifier of the investigated alert (FR-001) |
| alert_origin | enum: `connected_source` \| `analyst_submitted` | Intake path (FR-001) |
| analyst_id | string | Initiating analyst identity |
| agent_execution_id | UUID | Workload execution identity (Constitution III) |
| scope | text | Investigation scope statement |
| status | enum: `created`, `running`, `completed`, `partially_completed`, `denied`, `failed_safely`, `cancelled`, `budget_exhausted` | Terminal statuses per FR-004 |
| workflow_state | enum | Current state-machine state (see State Machine) |
| termination_reason | text, nullable | Exact reason for any non-completed end (FR-032) |
| started_at / completed_at | timestamp | FR-013 |
| limits | JSON (BudgetLimits) | Effective limits snapshot (FR-031) |
| spec_version / app_version / model_version / policy_version | string | Constitution VII |

Rules: same `alert_id` may appear in many cases; no automatic linking (clarification Q2). Status transitions are one-way into terminal states.

### CaseLink

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id_a / case_id_b | UUID | Linked cases |
| linked_by | string | Analyst identity (FR-003; single role per clarification Q3) |
| reason | text | |

Only sanctioned cross-case association.

### EvidenceItem

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | Isolation (FR-003) |
| source | string | Source system (FR-008) |
| source_record_id | string, nullable | Original event identifier when available |
| collected_at | timestamp | Collection timestamp |
| event_at | timestamp, nullable | Event timestamp |
| trust_classification | enum: `direct_observation`, `correlated`, `analyst_provided`, `unverified_external` | FR-008/FR-009 |
| content | JSON/text | Verbatim retrieved content (never sanitized) |
| size_bytes | int | Budget accounting |
| transformation_history | JSON list | Constitution IV |
| manipulation_flag | bool | Set when instruction patterns detected (FR-027) |
| tool_operation_id | UUID | Producing tool call |

### Claim (Finding)

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| statement | text | Material factual assertion |
| claim_type | enum: `direct_observation`, `correlation`, `inference`, `analyst_provided`, `unverified_external` | FR-009/FR-010 |
| support_status | enum: `supported`, `unsupported`, `inferred`, `inconclusive` | FR-007/FR-011 |
| confidence | enum: `high`, `medium`, `low`, `inconclusive` | Qualitative — not calibrated probability (Constitution IV) |
| material | bool | Material claims require evidence links or explicit labeling |

### ClaimEvidenceLink

| Field | Type | Notes |
|---|---|---|
| claim_id / evidence_id | UUID | |
| relationship | enum: `supports`, `contradicts`, `inconclusive` | FR-008/FR-012 |

Validation: every Claim with `material=true` and `support_status=supported` MUST have ≥1 `supports` link (FR-007). Missing evidence is represented on the claim (`support_status`), not fabricated links.

### Hypothesis

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| statement | text | Candidate explanation |
| evaluation | enum: `supported`, `rejected`, `inconclusive` | FR-015 |
| confirming_evidence_needed | text | What would confirm it |
| rejecting_evidence_needed | text | What would reject it |
| claim_ids | UUID list | Related claims |

### AffectedEntity

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| entity_type | enum: `user`, `endpoint`, `application`, `ip_address`, `process`, `file`, `other` | FR-014 |
| identifier | string | Normalized identifier |
| evidence_ids | UUID list | Provenance |

### TimelineEvent

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| event_at | timestamp | Deterministic ordering (Constitution V) |
| description | text | |
| evidence_ids | UUID list | Every timeline entry evidence-backed |

### InvestigationReport

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | One report per case (partial or complete) |
| report_kind | enum: `complete`, `partial` | FR-032 |
| content | JSON | Structured document with all FR-013 sections |
| verified | bool | Output verifier passed (secret scan, claim-evidence check) |
| generated_at | timestamp | |

Report `content` sections (schema-validated): case_id, alert_id, status, alert_summary, scope, timeline, affected_entities, findings, hypotheses, supporting_evidence, contradicting_or_inconclusive_evidence, missing_information, confidence_per_conclusion, severity_assessment, recommended_queries, response_action_proposals, limitations, data_sources_consulted, tool_operations, started_at, completed_at.

### ResponseActionProposal

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| action_description | text | Proposal only, never executed (FR-016) |
| affected_resources | JSON list | |
| evidence_ids | UUID list | |
| expected_impact / risk / rollback_method | text | |

### ToolOperation

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | FR-029 |
| agent_execution_id | UUID | |
| tool_name / operation | string | From static registry (FR-021) |
| target_resource | string | |
| parameters_redacted | JSON | Securely redacted (Constitution VII) |
| authorization_decision_id | UUID | Every op has a decision (FR-022) |
| outcome | enum: `success`, `denied`, `failed`, `malformed_result`, `timeout` | |
| requested_at / completed_at | timestamp | |

### AuthorizationDecision

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| agent_identity / analyst_id | string | Checked inputs (FR-022) |
| operation / target_resource | string | |
| budget_snapshot | JSON | Remaining budgets at decision time |
| decision | enum: `allow`, `deny` | Deny by default; absence/ambiguity → deny |
| reason | text | Recorded for denials (FR-018); denials never reveal existence of inaccessible data (FR-019) |

### BudgetLedger

| Field | Type | Notes |
|---|---|---|
| case_id | UUID | |
| elapsed_seconds / tool_operations_used / evidence_items / evidence_bytes / model_calls / cost_units / retries_by_operation | counters | Enforced against `InvestigationCase.limits` (FR-031/FR-032) |

### AuditEvent

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | |
| sequence | int | Ordered per case (FR-028) |
| event_type | enum | `case_created`, `scope_set`, `state_transition`, `source_accessed`, `tool_requested`, `authorization_decision`, `tool_result`, `tool_failure`, `evidence_collected`, `claim_generated`, `policy_denial`, `manipulation_detected`, `budget_consumed`, `report_generated`, `feedback_recorded`, `case_linked`, `secret_redacted`, `security_event` |
| actor | string | user / agent / system identity |
| payload | JSON | Redacted structured detail |
| prev_hash / event_hash | string | SHA-256 hash chain (tamper evidence; FR-030) |
| occurred_at | timestamp | |

Append-only; no application write path for UPDATE/DELETE.

### AnalystFeedback

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| case_id | UUID | Case-scoped only (FR-003) |
| analyst_id | string | |
| rating | enum: `useful`, `partially_useful`, `not_useful` | FR-034 |
| corrections | text, nullable | |
| irrelevant_evidence_ids | UUID list | |
| final_disposition | text, nullable | |

### RegisteredTool (static config, not DB)

| Field | Type | Notes |
|---|---|---|
| name / version | string | FR-021; version identifier per Constitution |
| operation | string | Single narrow read-only operation |
| input_schema / output_schema | JSON Schema | Typed contracts |
| authorization_scope | string | |
| timeout_seconds / max_result_bytes | int | |
| error_classification | enum list | |

## State Machine (workflow_state)

Normal path: `RECEIVE_ALERT → VALIDATE_REQUEST → AUTHORIZE → CLASSIFY_ALERT → CREATE_INVESTIGATION_PLAN → COLLECT_EVIDENCE → NORMALIZE_EVIDENCE → FORM_HYPOTHESES → VALIDATE_HYPOTHESES → PRODUCE_REPORT → VERIFY_OUTPUT → COMPLETE`

Terminal states: `ACCESS_DENIED`, `INCOMPLETE_EVIDENCE`, `SOURCE_UNAVAILABLE`, `POLICY_BLOCKED`, `BUDGET_EXCEEDED`, `VALIDATION_FAILED`, `CANCELLED`, `SYSTEM_ERROR`.

Each state defines (in code, per Constitution V): input schema, output schema, permitted tools, entry/exit conditions, max retries (≤ configured retry limit), timeout, failure transition. Analyst cancellation (clarification Q1) transitions any non-terminal state → `CANCELLED` after safe stop + partial report.

Terminal-state → case-status mapping: `COMPLETE→completed`; `BUDGET_EXCEEDED→budget_exhausted`; `CANCELLED→cancelled`; `ACCESS_DENIED/POLICY_BLOCKED→denied`; `INCOMPLETE_EVIDENCE/SOURCE_UNAVAILABLE→partially_completed`; `VALIDATION_FAILED/SYSTEM_ERROR→failed_safely`.
