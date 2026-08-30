# Investigation Workflow

The investigation runs inside an explicit, deterministic state machine
(`src/harness/orchestrator/machine.py`). This satisfies Constitution
Principle V: every state, transition, retry, timeout, and failure path is
inspectable code — nothing is decided by the model.

## Normal path

```
RECEIVE_ALERT
    → VALIDATE_REQUEST
    → AUTHORIZE
    → CLASSIFY_ALERT
    → CREATE_INVESTIGATION_PLAN
    → COLLECT_EVIDENCE
    → NORMALIZE_EVIDENCE
    → FORM_HYPOTHESES
    → VALIDATE_HYPOTHESES
    → PRODUCE_REPORT
    → VERIFY_OUTPUT
    → COMPLETE
```

## Terminal states

| Terminal state | Case status | Typical cause |
|---|---|---|
| `COMPLETE` | `completed` | Normal finish, report verified |
| `ACCESS_DENIED` | `denied` | Authorization cannot be established; alert retrieval denied |
| `POLICY_BLOCKED` | `denied` | Policy denial that blocks the workflow |
| `INCOMPLETE_EVIDENCE` | `partially_completed` | Evidence collection failure path |
| `SOURCE_UNAVAILABLE` | `partially_completed` | Connector down during a required step |
| `BUDGET_EXCEEDED` | `budget_exhausted` | Any of the five limits reached |
| `VALIDATION_FAILED` | `failed_safely` | Schema/verification failure (incl. output verifier) |
| `CANCELLED` | `cancelled` | Analyst cancellation |
| `SYSTEM_ERROR` | `failed_safely` | Unexpected exception |

Every investigation ends in exactly one terminal state (FR-004 / SC-009), and
the mapping above is exhaustive — a test
(`tests/unit/test_machine.py::test_every_terminal_state_maps_to_status`)
enforces it.

## What each state does

| State | Actions | Permitted tools |
|---|---|---|
| `RECEIVE_ALERT` | Case exists; audit `case_created`, `scope_set` already emitted | — |
| `VALIDATE_REQUEST` | Intake validated (origin, alert ID/content, limit overrides) | — |
| `AUTHORIZE` | Analyst claims present; empty claim set → `ACCESS_DENIED` | — |
| `CLASSIFY_ALERT` | Retrieve alert detail (connected) or store analyst-submitted content as `analyst_provided` evidence | `alert_source.get_alert` |
| `CREATE_INVESTIGATION_PLAN` | Scope confirmation (single-alert plan) | — |
| `COLLECT_EVIDENCE` | Retrieve related events; store verbatim with provenance | `alert_source.get_related_events`, `endpoint_telemetry.get_events`, `identity_context.*` |
| `NORMALIZE_EVIDENCE` | Deterministic timeline, entity extraction, direct-observation claims; entity enrichment lookups | `endpoint_telemetry.get_events`, `identity_context.*` |
| `FORM_HYPOTHESES` | One model call over demarcated evidence; output validated; claims typed `inference` | — (model has no tools) |
| `VALIDATE_HYPOTHESES` | Deterministic evidence linkage; unsupported "supported" degrades to inconclusive; proposals derived | — |
| `PRODUCE_REPORT` | Build schema-valid `ReportContent` (all FR-013 sections) | — |
| `VERIFY_OUTPUT` | Secret scan + claim-evidence completeness; failure → `VALIDATION_FAILED` + `security_event` | — |
| `COMPLETE` | Persist verified report; audit `report_generated` | — |

Per-state configuration also fixes **max retries** (≤ 2), a **timeout**, and a
**failure transition** — e.g. `COLLECT_EVIDENCE` fails into
`INCOMPLETE_EVIDENCE`, `CLASSIFY_ALERT` into `SOURCE_UNAVAILABLE`.

## Tool gating per state

The state machine exposes `permitted_tools()` for the current state, and the
tool invoker intersects that set with the static registry before the policy
check. A tool that is registered but not permitted *in the current state* is
denied. This yields least-privilege tool access per workflow phase.

## Cancellation (FR-005a)

Investigations run autonomously — there are no mid-run analyst checkpoints —
but the analyst may cancel at any time:

- `POST /cases/{id}/cancel` (or `states.request_cancel(case_id)`) sets a
  cooperative flag.
- The orchestrator checks the flag **between states**; when set, the next
  transition goes to `CANCELLED`.
- Finalization produces a **partial report** describing completed work and
  records termination reason `cancelled by analyst`.

## Failure handling

All failure paths converge on a single `_finalize()` routine that:

1. Transitions to the appropriate terminal state (never leaves a case
   in-flight).
2. Sets `status`, `termination_reason` (exact, human-readable), and
   `completed_at`.
3. Generates a **partial report** listing completed work, unavailable
   evidence, and the termination reason (FR-032).
4. Commits — audit events emitted along the way are preserved.

Two invariants hold on every failure (FR-020, verified by
`tests/unit/test_fail_safe.py`):

- No failure ever expands authorization or relaxes a control.
- A failed source is never silently substituted with an unauthorized one
  (FR-024) — the gap is *named* in the report's limitations instead.

## Budget interaction

`BudgetService` is consulted before every tool call and model call. When a
limit is hit, `BudgetExceeded` propagates to the workflow's exception
boundary, which transitions to `BUDGET_EXCEEDED` and finalizes with the exact
limit name in the termination reason, e.g.:

```
budget exhausted: max_tool_operations (tool budget exhausted)
```

## Sequence example (ALERT-1001, happy path)

```
case_created → scope_set
state_transition RECEIVE_ALERT→VALIDATE_REQUEST→AUTHORIZE→CLASSIFY_ALERT
tool_requested(alert_source.get_alert) → authorization_decision(allow)
  → budget_consumed → source_accessed → tool_result → evidence_collected
state_transition →CREATE_INVESTIGATION_PLAN→COLLECT_EVIDENCE
tool_requested(get_related_events) → … → evidence_collected ×3
state_transition →NORMALIZE_EVIDENCE
claim_generated ×N (direct_observation)
tool_requested(endpoint_telemetry/identity_context) → … enrichment
state_transition →FORM_HYPOTHESES
budget_consumed(model_call) → claim_generated (inference)
state_transition →VALIDATE_HYPOTHESES→PRODUCE_REPORT→VERIFY_OUTPUT→COMPLETE
report_generated
```

A reviewer can replay exactly this sequence from
`GET /cases/{id}/audit` — see [audit.md](audit.md).
