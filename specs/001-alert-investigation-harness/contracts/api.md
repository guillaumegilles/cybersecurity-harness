# API Contract: Read-Only Alert Investigation Harness

**Date**: 2026-08-28 | **Plan**: [../plan.md](../plan.md)

All endpoints require `Authorization: Bearer <token>` (analyst identity + data-source claims). All responses are JSON. All errors use `{ "error": { "code": string, "message": string } }`; authorization failures return 403 without revealing whether the resource exists (FR-019). Every request is case-scoped where applicable and emits audit events.

## Cases

### POST /cases

Start an investigation from one alert (FR-001, FR-002).

Request:
```json
{
  "alert": {
    "origin": "connected_source | analyst_submitted",
    "alert_id": "string (required when origin=connected_source)",
    "content": "object (required when origin=analyst_submitted; labeled analyst-provided, treated as untrusted)"
  },
  "limit_overrides": { "max_elapsed_seconds": 600, "...": "optional; validated against hard floors/ceilings; cannot disable limits" }
}
```

Response `201`:
```json
{ "case_id": "uuid", "status": "created", "workflow_state": "RECEIVE_ALERT", "limits": { } }
```

Errors: `400` invalid alert; `403` analyst not authorized for alert source.

### GET /cases/{case_id}

Case summary: status, workflow_state, termination_reason, timestamps, budget consumption. `403` if analyst lacks access per organizational policy.

### POST /cases/{case_id}/cancel

Cancel a running investigation (clarification Q1). Safe stop, partial report, terminal status `cancelled`. Response `202`: `{ "case_id": "...", "status": "cancelling" }`. `409` if already terminal.

### POST /cases/{case_id}/links

Explicitly link two cases (FR-003). Body: `{ "other_case_id": "uuid", "reason": "string" }`. `403` unless analyst can access both cases.

## Reports

### GET /cases/{case_id}/report

Structured report (complete or partial) with all FR-013 sections. Query `?format=markdown` returns rendered Markdown. `404` (as 403-safe) if no report yet.

### GET /cases/{case_id}/claims/{claim_id}/evidence

Provenance inspection (FR-012): returns supporting/contradicting/inconclusive evidence for a claim with full provenance metadata (source, source_record_id, collected_at, event_at, trust_classification, relationship).

```json
{
  "claim": { "id": "uuid", "statement": "...", "claim_type": "...", "support_status": "...", "confidence": "..." },
  "evidence": [
    { "id": "uuid", "relationship": "supports", "source": "edr", "source_record_id": "evt-123",
      "collected_at": "...", "event_at": "...", "trust_classification": "direct_observation", "content": { } }
  ],
  "missing_evidence": "text or null"
}
```

## Feedback

### POST /cases/{case_id}/feedback

FR-034. Body:
```json
{ "rating": "useful | partially_useful | not_useful", "corrections": "string?", "irrelevant_evidence_ids": ["uuid"], "final_disposition": "string?" }
```
Response `201`. Case-scoped; recorded in audit.

## Audit (reviewer access — single role per clarification Q3)

### GET /cases/{case_id}/audit

Ordered audit events for reconstruction (FR-028–FR-030). Query params: `after_sequence`, `event_type`. Response includes hash-chain fields.

### GET /cases/{case_id}/audit/verify

Recomputes the hash chain; returns `{ "intact": true|false, "events_checked": n, "first_broken_sequence": n|null }`.

## Non-endpoints (explicitly absent)

No endpoint exists to: modify or delete audit events, execute response actions, register tools at runtime, write cross-case memory, or modify evidence. Their absence is a contract guarantee (FR-017, FR-030).
