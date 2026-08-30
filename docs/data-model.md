# Data Model

Implementation: `src/harness/storage/models.py` (SQLAlchemy) and
`src/harness/storage/schemas.py` (Pydantic). The authoritative design document
is [`specs/001-alert-investigation-harness/data-model.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/data-model.md).

## Entity relationship overview

```
InvestigationCase 1 ──── * EvidenceItem ──┐
        │                                 │ * ClaimEvidenceLink *
        ├──── * Claim ────────────────────┘
        ├──── * Hypothesis (claim_ids)
        ├──── * AffectedEntity (evidence_ids)
        ├──── * TimelineEvent (evidence_ids)
        ├──── * ToolOperation ── 1 AuthorizationDecision
        ├──── 1 BudgetLedger
        ├──── * InvestigationReport
        ├──── * ResponseActionProposal
        ├──── * AnalystFeedback
        ├──── * AuditEvent (ordered, hash-chained)
        └──── * CaseLink (explicit, analyst-created)
```

Every case-scoped entity carries `case_id` and is reachable **only** through
`CaseScopedRepository`, which filters all queries by the active `CaseContext`.

## Entities

### InvestigationCase

The isolated container for one alert investigation.

| Field | Notes |
|---|---|
| `id` | UUID, unique per investigation (FR-002) |
| `alert_id` / `alert_origin` | `connected_source` or `analyst_submitted` (FR-001) |
| `analyst_id` | Initiating analyst |
| `agent_execution_id` | Fresh workload identity per run (Constitution III) |
| `status` | `created·running·completed·partially_completed·denied·failed_safely·cancelled·budget_exhausted` (FR-004) |
| `workflow_state` | Current/final state-machine state |
| `termination_reason` | Exact reason on any non-completed end (FR-032) |
| `limits` | Effective `BudgetLimits` snapshot (FR-031) |
| `spec/app/model/policy_version` | Reproducibility metadata (Constitution VII) |

The same alert may be investigated many times; each run is a new, fully
isolated case with no automatic linking.

### EvidenceItem

A verbatim unit of retrieved information with full provenance (FR-008).

| Field | Notes |
|---|---|
| `source` / `source_record_id` | Origin system and original event ID |
| `collected_at` / `event_at` | Collection vs. event timestamps |
| `trust_classification` | `direct_observation` · `correlated` · `analyst_provided` · `unverified_external` |
| `content` | **Verbatim** retrieved content — never sanitized |
| `manipulation_flag` | Set when the instruction detector matches (FR-027) |
| `transformation_history` | Constitution IV provenance trail |
| `tool_operation_id` | The producing tool call |

### Claim (finding)

A material factual assertion (FR-007, FR-009–FR-011).

| Field | Values |
|---|---|
| `claim_type` | `direct_observation` · `correlation` · `inference` · `analyst_provided` · `unverified_external` |
| `support_status` | `supported` · `unsupported` · `inferred` · `inconclusive` |
| `confidence` | `high` · `medium` · `low` · `inconclusive` (qualitative — never a calibrated probability) |

**Invariant:** a material claim with `support_status = supported` must have at
least one `supports` evidence link — enforced at generation time and again by
the report verifier.

### ClaimEvidenceLink

Claim ↔ evidence with `relationship ∈ {supports, contradicts, inconclusive}`.
Both ends must belong to the same case (checked by the repository).

### Hypothesis

A candidate explanation with `evaluation ∈ {supported, rejected,
inconclusive}` plus the evidence that would **confirm** and **reject** it
(FR-015) — the basis for the report's alternative-hypotheses section and
recommended next queries.

### AffectedEntity

`entity_type ∈ {user, endpoint, application, ip_address, process, file,
other}` with the evidence IDs it was derived from (FR-014).

### TimelineEvent

Chronological (`event_at`-ordered) events, each backed by evidence IDs.
Ordering is deterministic code, not model output.

### InvestigationReport

`report_kind ∈ {complete, partial}`; `content` is the JSON document validated
against the `ReportContent` Pydantic schema containing **all 20 FR-013
sections**; `verified` records whether the output gate passed.

### ResponseActionProposal

Proposal-only response actions (FR-016): description, affected resources,
evidence IDs, expected impact, risk, rollback method. No entity or field in
the system represents an *executed* action.

### ToolOperation & AuthorizationDecision

Every tool call produces one `ToolOperation` (redacted parameters, outcome ∈
`success·denied·failed·malformed_result·timeout·oversized_result`) linked to
exactly one `AuthorizationDecision` (checked inputs, budget snapshot,
allow/deny, reason). This satisfies FR-022/FR-029: no tool operation without a
recorded decision.

### BudgetLedger

Per-case counters (elapsed seconds, tool ops, evidence items/bytes, model
calls, per-operation retries) enforced against the case's `limits`.

### AuditEvent

Append-only, per-case sequenced, hash-chained — see [audit.md](audit.md).

### AnalystFeedback

Rating (`useful·partially_useful·not_useful`), corrections,
irrelevant-evidence flags, final disposition (FR-034). Case-scoped like all
other entities.

### CaseLink

The **only** sanctioned cross-case association: created explicitly by an
analyst with access to both cases; audited on both sides.

## Report content sections (FR-013)

`ReportContent` requires: `case_id`, `alert_id`, `status`, `alert_summary`,
`scope`, `timeline`, `affected_entities`, `findings`, `hypotheses`,
`contradicting_or_inconclusive_evidence`, `missing_information`,
`severity_assessment`, `recommended_queries`, `response_action_proposals`,
`limitations`, `data_sources_consulted`, `tool_operations`, `started_at`,
`completed_at`.

## Trust and claim-type semantics

| Label | Meaning | Producer |
|---|---|---|
| `direct_observation` | Retrieved verbatim from an approved source with a record ID | Connectors via evidence store |
| `correlated` / `correlation` | Derived deterministically from multiple observations | Deterministic analysis code |
| `inference` | Model-generated hypothesis material | Model gateway → claims service |
| `analyst_provided` | Submitted by the analyst (treated as untrusted) | Case intake |
| `unverified_external` | External information without verification | Reserved |

The system never promotes a label upward (e.g. inference → observation);
tests in `tests/integration/test_provenance.py` verify the labels survive
end-to-end.
