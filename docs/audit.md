# Audit Trail

Implementation: `src/harness/audit/service.py`. The audit trail satisfies
FR-028–FR-030 and Constitution Principle VII: every investigation is fully
reconstructable, and the investigating agent has no path to modify its own
record.

## Properties

| Property | Mechanism |
|---|---|
| **Complete** | Every lifecycle step emits an event (see catalogue below); an integration test reconstructs a full investigation from audit alone |
| **Ordered** | Per-case monotonically increasing `sequence` with a DB uniqueness constraint; gap-free by construction |
| **Append-only** | `AuditService`'s public API is exactly `append`, `list_events`, `verify_chain` (test-asserted); no HTTP mutation methods exist |
| **Tamper-evident** | Per-case SHA-256 hash chain: each event stores `prev_hash` and `event_hash` over its canonical JSON; edits, insertions, and deletions all break verification |
| **Redacted** | Payloads pass through the secret-redaction processors before hashing/storage |
| **Attributable** | Every event names an `actor` (analyst, agent execution ID, or system component) |

## Hash chain

```
event_hash(n) = SHA-256( canonical_json({
    case_id, sequence, event_type, actor, payload,
    occurred_at,                       # canonical UTC ISO form
    prev_hash = event_hash(n-1)        # "" for the first event
}) )
```

`GET /cases/{id}/audit/verify` recomputes the chain server-side and reports
the first broken sequence, if any. Tests demonstrate detection of both direct
payload rewrites and event deletion.

> Note: the hash chain provides *tamper evidence*, not tamper prevention
> against an attacker with direct database write access. Production pilots
> should layer WORM/object-lock storage or signed events on top (planned for
> the PostgreSQL pilot feature).

## Event catalogue

| Event type | Emitted when | Actor |
|---|---|---|
| `case_created` | Investigation case created | analyst |
| `scope_set` | Investigation scope recorded | system |
| `state_transition` | Every workflow state change (`{from, to}`) | orchestrator |
| `tool_requested` | Before any tool call (redacted params) | agent execution ID |
| `authorization_decision` | Every policy decision (`allow`/`deny` + reason + decision ID) | agent execution ID |
| `policy_denial` | Additionally on every denial | policy_engine |
| `source_accessed` | Successful access to a data source | agent execution ID |
| `tool_result` | Successful tool call (outcome + size) | tool_invoker |
| `tool_failure` | Failed/malformed/oversized/unavailable tool call | tool_invoker |
| `evidence_collected` | Evidence item persisted (ID, source, record ID, size) | agent execution ID |
| `manipulation_detected` | Instruction patterns found in untrusted content | instruction_detector |
| `claim_generated` | Claim created (ID + type) | claims_service |
| `budget_consumed` | Any budget consumption (kind + snapshot) | orchestrator |
| `report_generated` | Report persisted (kind + verified flag) | report_generator |
| `feedback_recorded` | Analyst feedback stored | analyst |
| `case_linked` | Explicit case link (audited on both cases) | analyst |
| `secret_redacted` | Reserved: explicit redaction occurrences | system |
| `security_event` | Output-verifier failure, tamper attempt, or other security-relevant anomaly | component |

The event-type set is a closed enum — `append()` rejects unknown types.

## Reviewer reconstruction

An authorized reviewer can answer, from `GET /cases/{id}/audit` alone:

1. **What was accessed** — `source_accessed`, `evidence_collected`
2. **What was requested and decided** — `tool_requested` +
   `authorization_decision` (+ `policy_denial`)
3. **What the tools returned** — `tool_result` / `tool_failure`
4. **How the workflow progressed** — the `state_transition` sequence from
   `RECEIVE_ALERT` to the terminal state
5. **What was concluded** — `claim_generated` events, then the report itself
6. **What it cost** — `budget_consumed` snapshots
7. **What the analyst thought** — `feedback_recorded`

`tests/integration/test_audit_completeness.py` automates exactly this
reconstruction, including the invariant that every requested tool has a
recorded authorization decision (FR-029).

## Access control

Audit records are case-scoped: a reviewer sees a case's audit trail only if
organizational policy grants access to that case (single-role model — every
authenticated analyst is a reviewer for cases they can access). Unauthorized
access returns the same `403` as a nonexistent case.
