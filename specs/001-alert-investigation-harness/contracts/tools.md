# Tool Contracts: Registered Read-Only Investigation Tools

**Date**: 2026-08-28 | **Plan**: [../plan.md](../plan.md)

The tool registry is static configuration loaded at startup (FR-021). No runtime registration. The model never invokes tools directly — orchestrator states request tool operations, and every request passes the Policy Engine (FR-022) before execution. All tools are strictly read-only.

Common contract for every tool (Constitution tool boundaries):

- Pydantic-validated input and output schemas
- Declared `authorization_scope` and permitted `operation`
- `timeout_seconds` and `max_result_bytes` limits
- Error classification: `unavailable`, `malformed_result`, `unauthorized`, `timeout`, `oversized_result`
- Version identifier; every invocation produces `tool_requested`, `authorization_decision`, and `tool_result`/`tool_failure` audit events
- Results are stored verbatim as EvidenceItems with provenance; instruction-pattern detection runs on all results (FR-025–FR-027)

## Tool 1: `alert_source.get_alert`

Retrieve alert detail from the approved alert source (SIEM-like, synthetic in MVP).

Input: `{ "alert_id": "string" }`
Output: `{ "alert_id": "string", "rule_name": "string", "severity": "string", "detected_at": "timestamp", "raw": { } }`

## Tool 2: `alert_source.get_related_events`

Retrieve events related to an alert within case scope.

Input: `{ "alert_id": "string", "start": "timestamp", "end": "timestamp", "max_results": "int <= 200" }`
Output: `{ "events": [ { "event_id": "string", "event_at": "timestamp", "event_type": "string", "raw": { } } ], "truncated": "bool" }`

## Tool 3: `endpoint_telemetry.get_events`

Retrieve endpoint telemetry (EDR-like: process, file, network events) for a specific endpoint.

Input: `{ "endpoint_id": "string", "start": "timestamp", "end": "timestamp", "event_types": ["process|file|network"], "max_results": "int <= 200" }`
Output: `{ "events": [ { "event_id": "string", "event_at": "timestamp", "event_type": "string", "raw": { } } ], "truncated": "bool" }`

## Tool 4: `identity_context.get_user`

Retrieve identity context for a user.

Input: `{ "user_id": "string" }`
Output: `{ "user_id": "string", "display_name": "string", "department": "string", "account_status": "string", "risk_notes": "string?" }`

## Tool 5: `identity_context.get_asset`

Retrieve asset context and criticality.

Input: `{ "asset_id": "string" }`
Output: `{ "asset_id": "string", "hostname": "string", "owner": "string", "criticality": "low|medium|high|critical", "environment": "string" }`

Five narrow operations across three connectors (alert source, endpoint telemetry, identity/asset context) — within the constitutional cap of three approved read-only sources.

## Authorization inputs checked per invocation (FR-022)

1. Agent execution identity valid and bound to the case
2. Initiating analyst authorized for the target source (token claims)
3. Operation within case scope
4. Operation ∈ tool's declared operation
5. Target resource within authorization scope
6. Remaining budget (tool ops, evidence volume, time) sufficient

Any check absent, ambiguous, or failed → deny (recorded, FR-018), without revealing whether inaccessible data exists (FR-019). Denials are authoritative; the orchestrator does not probe alternative operations (Constitution III).
