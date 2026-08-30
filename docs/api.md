# API Reference

Base URL (local): `http://localhost:8000` — interactive docs at `/docs`.

Design contract: [`specs/001-alert-investigation-harness/contracts/api.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/contracts/api.md).

## Authentication

All endpoints require a bearer token:

```
Authorization: Bearer <JWT>
```

Tokens carry the analyst ID (`sub`) and the data sources the analyst is
authorized to reach (`sources`). In dev/eval, issue one with:

```bash
python -m harness.cli issue-token --analyst alice \
  --sources alert_source,endpoint_telemetry,identity_context
```

There is a single user role: any authenticated analyst may investigate, view
audit records, and link cases they can access.

## Error semantics

- Errors use the envelope `{"error": {"code": "...", "message": "..."}}`.
- `401` — missing/invalid token.
- `403` — **both** "unauthorized" and "does not exist" (FR-019). The API
  never reveals whether an inaccessible resource exists.
- `400` — invalid intake (missing alert ID/content, out-of-bounds limit
  overrides).
- `409` — action conflicts with case state (e.g. cancelling a terminal case).
- `422` — request-body schema violations.

The API exposes **no** PUT/PATCH/DELETE methods anywhere, and no endpoint for
executing response actions, mutating audit records, or registering tools —
this absence is contract-tested.

---

## Cases

### `POST /cases` — start an investigation

Creates an isolated case and runs the investigation (synchronously in
dev/eval).

Request:

```json
{
  "alert": {
    "origin": "connected_source",      // or "analyst_submitted"
    "alert_id": "ALERT-1001",          // required for connected_source
    "content": { "...": "..." }        // required for analyst_submitted
  },
  "limit_overrides": {                 // optional; validated against hard bounds
    "max_tool_operations": 25
  }
}
```

Analyst-submitted content is labeled `analyst_provided` and treated as
untrusted evidence.

Response `201`:

```json
{
  "case_id": "uuid",
  "status": "completed",
  "workflow_state": "COMPLETE",
  "limits": { "max_elapsed_seconds": 600, "max_tool_operations": 50, "...": 0 }
}
```

`status` is always one of the six terminal statuses (or `created`/`running`
for asynchronous deployments).

### `GET /cases/{case_id}` — case summary

Returns status, workflow state, termination reason, timestamps, and effective
limits.

### `POST /cases/{case_id}/cancel` — cancel a running investigation

Cooperative cancellation; the run stops safely between states and produces a
partial report. Returns `202 {"status": "cancelling"}`, or `409` if the case
is already terminal.

### `POST /cases/{case_id}/links` — explicitly link two cases

```json
{ "other_case_id": "uuid", "reason": "same campaign" }
```

Requires access to **both** cases; the link is audited on both sides. This is
the only sanctioned cross-case association.

---

## Reports

### `GET /cases/{case_id}/report` — structured report

Returns the latest (complete or partial) report:

```json
{
  "report_id": "uuid",
  "report_kind": "complete",
  "verified": true,
  "content": { /* all 20 FR-013 sections — see docs/data-model.md */ }
}
```

Query `?format=markdown` returns a rendered Markdown document
(`text/markdown`) instead.

### `GET /cases/{case_id}/claims/{claim_id}/evidence` — provenance inspection

For any finding in the report, returns its full evidence provenance (FR-012):

```json
{
  "claim": {
    "id": "uuid",
    "statement": "Observed process_creation (source alert_source, record SIEM-9002)",
    "claim_type": "direct_observation",
    "support_status": "supported",
    "confidence": "high"
  },
  "evidence": [
    {
      "id": "uuid",
      "relationship": "supports",
      "source": "alert_source",
      "source_record_id": "SIEM-9002",
      "collected_at": "2026-08-28T09:15:02+00:00",
      "event_at": "2026-08-28T09:15:02+00:00",
      "trust_classification": "direct_observation",
      "content": { "...": "verbatim retrieved content" }
    }
  ],
  "missing_evidence": null
}
```

---

## Audit

### `GET /cases/{case_id}/audit` — ordered audit trail

Query parameters: `after_sequence` (int), `event_type` (string filter).

```json
{
  "case_id": "uuid",
  "events": [
    {
      "sequence": 1,
      "event_type": "case_created",
      "actor": "alice",
      "payload": { "alert_id": "ALERT-1001", "...": "..." },
      "prev_hash": "",
      "event_hash": "sha256…",
      "occurred_at": "2026-08-28T10:00:00+00:00"
    }
  ]
}
```

Payloads are secret-redacted. Event types are listed in [audit.md](audit.md).

### `GET /cases/{case_id}/audit/verify` — hash-chain verification

```json
{ "intact": true, "events_checked": 42, "first_broken_sequence": null }
```

Recomputes the SHA-256 chain server-side; any edit, insertion, or deletion of
an audit event flips `intact` to `false` and names the first broken sequence.

---

## Feedback

### `POST /cases/{case_id}/feedback` — analyst feedback

Only accepted once the investigation is terminal (`409` otherwise).

```json
{
  "rating": "useful",                        // useful | partially_useful | not_useful
  "corrections": "second hypothesis is more likely",
  "irrelevant_evidence_ids": ["uuid"],
  "final_disposition": "true positive, contained manually"
}
```

Response `201` with `feedback_id`. Feedback is case-scoped and audited
(`feedback_recorded`).
