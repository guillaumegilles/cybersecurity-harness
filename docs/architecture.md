# Architecture

## Design philosophy

The harness follows one governing idea from the project constitution:
**probabilistic reasoning may occur only inside a deterministic operational
envelope**. The language model assists with hypothesis generation and nothing
else. Authorization, budgets, workflow control, evidence handling, audit, and
output verification are deterministic code that the model cannot influence.

Three consequences shape the entire architecture:

1. **The model has no tools.** Tool selection and invocation happen in
   orchestrator states from a static registry. An injected "tool call" inside
   evidence is inert text.
2. **The model is never a policy enforcement point.** A single deterministic
   Policy Engine authorizes every tool operation deny-by-default, outside the
   model's reasoning.
3. **Model output is untrusted input.** It is parsed, schema-validated, and
   degraded to "inconclusive" whenever invalid — it can never mint an
   evidence-backed fact.

## Component map

```
                       ┌────────────────────────────────────────────┐
 Analyst ──JWT/HTTP──▶ │ API layer (src/harness/api)                │
                       │  routes_cases / reports / evidence /       │
                       │  audit / feedback · identity (stub JWT)    │
                       └───────────────┬────────────────────────────┘
                                       │
                       ┌───────────────▼────────────────────────────┐
                       │ Orchestrator (src/harness/orchestrator)    │
                       │  machine.py   deterministic state machine  │
                       │  states.py    concrete workflow execution  │
                       │  case_service case lifecycle, linking      │
                       │  budget.py    limit enforcement            │
                       └───┬─────────────┬──────────────┬───────────┘
                           │             │              │
            ┌──────────────▼──┐  ┌───────▼──────┐  ┌────▼─────────────┐
            │ Policy Engine   │  │ Tool Invoker │  │ Model Gateway    │
            │ (policy/)       │◀─│ (tools/)     │  │ (model/)         │
            │ deny-by-default │  │ static       │  │ FakeModel or     │
            │ single PEP      │  │ registry     │  │ litellm; NO tools│
            └──────────┬──────┘  └───────┬──────┘  └────┬─────────────┘
                       │                 │              │
                       │         ┌───────▼──────────┐   │ untrusted JSON
                       │         │ Connectors       │   ▼
                       │         │ (connectors/)    │  claims/hypotheses
                       │         │ 3 synthetic      │  (analysis/)
                       │         │ read-only sources│
                       │         └───────┬──────────┘
                       │                 │ verbatim content + provenance
                       │         ┌───────▼──────────┐
                       │         │ Evidence Store   │──▶ instruction
                       │         │ (evidence/)      │    detector
                       │         └───────┬──────────┘
                       ▼                 ▼
            ┌────────────────────────────────────────┐
            │ Audit Service (audit/)                 │
            │ append-only · SHA-256 hash chain       │
            ├────────────────────────────────────────┤
            │ Storage (storage/)                     │
            │ SQLAlchemy · case-scoped repositories  │
            └────────────────────────────────────────┘
```

## Components

### API layer — `src/harness/api/`

- **`app.py`** — FastAPI app factory, bearer-token auth dependency, uniform
  error envelope `{"error": {"code", "message"}}`.
- **`identity.py`** — `StubIdentityProvider` issuing/verifying signed JWTs
  carrying the analyst ID and per-source authorization claims
  (`sources: [...]`). Designed as a narrow `IdentityProvider` protocol so an
  organization's OIDC system can replace it without touching callers.
- **Routers** — cases (create/get/cancel/link), reports (JSON/Markdown),
  claim provenance, audit view + verification, feedback.

Authorization failures and nonexistent resources both return `403` with an
identical body (FR-019): the API never reveals whether inaccessible data
exists.

### Orchestrator — `src/harness/orchestrator/`

- **`machine.py`** — the explicit state machine: 12 workflow states, 8
  terminal states, a static transition table, per-state configuration
  (permitted tools, retries, timeout, failure transition), and a
  terminal-state → case-status mapping. Arbitrary jumps raise
  `InvalidTransition`; terminal states are final.
- **`states.py`** — the concrete run: retrieves the alert, collects related
  events, normalizes evidence into timeline/entities/claims, enriches
  entities via identity/asset lookups, generates hypotheses (model-assisted),
  derives proposals, produces and verifies the report. All exceptions funnel
  into a safe `_finalize()` that records the exact termination reason and
  emits a partial report (FR-032).
- **`case_service.py`** — case creation (both intake origins, limit-override
  validation, per-execution agent identity) and explicit case linking.
- **`budget.py`** — `BudgetService` enforcing the five limits with per-case
  ledgers and `budget_consumed` audit events. Exhaustion raises
  `BudgetExceeded`, which terminates the workflow safely.

### Policy — `src/harness/policy/`

- **`engine.py`** — `PolicyEngine.authorize()` is the single Policy
  Enforcement Point. It evaluates, in order: context completeness (absence or
  ambiguity → deny), prohibited-operation classes, registration + per-state
  permission, analyst source authorization, and budget. Every decision is
  persisted (`AuthorizationDecision`) and audited; denials additionally emit
  `policy_denial` events.
- **`rules.py`** — the explicit deny list mirroring FR-017 (isolate, block,
  disable, execute, upload, install, spawn, audit mutation, memory writes…)
  plus opaque denial reason codes.

### Tools — `src/harness/tools/`

- **`registry.py`** — a static, import-time dictionary of five
  `RegisteredTool` entries (frozen dataclasses) with Pydantic input schemas,
  authorization scopes, timeouts, and result-size limits. There is no
  runtime-registration function, by design.
- **`invoker.py`** — the only path to a connector. Sequence per call:
  audit `tool_requested` → policy check → budget consumption → input
  validation → connector execution → result-shape and size validation →
  evidence-ready result + `tool_result`/`tool_failure` audit events. A denial
  is authoritative: there is no retry-with-different-privileges or fallback
  source (FR-024).

### Connectors — `src/harness/connectors/`

Three synthetic, strictly read-only sources backed by fixture data
(`fixtures.py`): an alert source (SIEM-like), endpoint telemetry (EDR-like),
and identity/asset context (directory-like). Each supports an `AVAILABLE`
toggle for unavailable-dependency testing. A deliberately planted fake secret
in the fixtures backs the secret-leak test suite.

### Evidence — `src/harness/evidence/`

- **`store.py`** — persists retrieved content **verbatim** (never sanitized)
  with full provenance: source, source record ID, collection/event
  timestamps, trust classification, transformation history, and the producing
  tool operation. Runs the instruction detector on every item and emits
  `manipulation_detected` audit events when patterns match (FR-027).
- **`instruction_detector.py`** — deterministic regex/heuristic ruleset for
  instructions aimed at the agent (ignore-policy, exfiltration, command
  execution, permission grants, audit tampering, persistent-instruction
  attempts…).
- **`provenance.py`** — assembles claim → evidence views for the provenance
  inspection endpoint (FR-012).

### Analysis — `src/harness/analysis/`

- **`timeline.py` / `entities.py`** — deterministic timeline ordering and
  entity extraction (users, endpoints, applications, IPs, processes, files).
- **`claims.py`** — two claim paths: *direct-observation claims* generated
  deterministically from evidence with source record IDs, and
  *inference claims* derived from model hypotheses. Model output that is
  malformed, or "supported" without any direct evidence to link, degrades to
  `inconclusive` (FR-007/FR-011).
- **`proposals.py`** — response-action proposals (isolation, credential
  reset) generated only when a hypothesis is supported; always proposal-only
  with impact, risk, and rollback (FR-016).
- **`feedback.py`** — analyst rating/corrections/disposition, case-scoped.

### Model — `src/harness/model/`

- **`gateway.py`** — the narrow `ModelGateway` protocol with two
  implementations: `FakeModel` (deterministic, for dev/eval/tests) and
  `LiteLLMModel` (real providers, lazily imported). Selected by `FAKE_MODEL`.
- **`prompts.py`** — evidence enters the user prompt inside
  `<untrusted-evidence>` structural delimiters with an explicit
  data-not-instructions framing; evidence never appears in system prompts.

### Report — `src/harness/report/`

- **`generator.py`** — builds the schema-validated `ReportContent` (all 20
  FR-013 sections), persists it, and renders Markdown on demand. Partial
  reports on any early termination include completed work, unavailable
  evidence, and the exact termination reason.
- **`verifier.py`** — pre-delivery gate: secret-pattern scan (FR-035) and
  claim-evidence completeness check (no "supported" material claim without
  evidence). Failures produce `security_event` audit entries and a
  `VALIDATION_FAILED` terminal state — the report is withheld, never patched.

### Audit — `src/harness/audit/`

See [audit.md](audit.md). Append-only service; the public API is exactly
`append`, `list_events`, `verify_chain` (asserted by tests).

### Storage — `src/harness/storage/`

- **`models.py`** — 15 SQLAlchemy entities (see [data-model.md](data-model.md)).
- **`repositories.py`** — `CaseScopedRepository` requires an explicit
  `CaseContext` and filters every query by `case_id`; cross-case reads/writes
  raise `CaseIsolationError`. `get_case()` applies the access policy and
  returns `None` identically for missing and unauthorized cases.
- **`db.py`** — engine/session management. Schema via `create_all` for the
  SQLite dev/eval environment (alembic arrives with the PostgreSQL pilot).
- **`schemas.py`** — Pydantic domain and API schemas, including the
  `ReportContent` contract.

## Trust boundaries

| # | Boundary | Control |
|---|----------|---------|
| 1 | Analyst ↔ API | JWT authentication; per-source claims; 403-safe responses |
| 2 | Orchestrator ↔ Model | Model output parsed + validated; no authority, no tools |
| 3 | Orchestrator ↔ Tools/Connectors | Policy Engine per call; typed I/O; timeouts; size limits |
| 4 | Retrieved evidence ↔ Agent context | Treated as hostile; structural demarcation; instruction detector |
| 5 | Agent ↔ Audit store | Append-only service; hash chain; no mutation path |
| 6 | Case ↔ Case | Case-scoped repositories; explicit links only |

## Key design decisions

Recorded in full in
[`specs/001-alert-investigation-harness/research.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/research.md):

| Decision | Why |
|----------|-----|
| Hand-rolled state machine, no agent framework | Constitution requires explicit, inspectable orchestration; frameworks embed implicit control flow and framework-managed memory |
| Model has zero tool access | Structurally eliminates the largest prompt-injection consequence class |
| SQLite dev / PostgreSQL-compatible schema | Zero-friction evaluation environment with a pilot migration path |
| Hash-chained audit table | Tamper evidence with no new dependencies; queryable for reviewer reconstruction |
| Repository-layer case isolation | Works identically on SQLite and PostgreSQL; structural, not conventional |
| Stub JWT identity behind a protocol | Honors the "org identity system" assumption without blocking the vertical slice |
