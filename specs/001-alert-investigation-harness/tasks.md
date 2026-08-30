# Tasks: Read-Only Alert Investigation Harness

**Input**: Design documents from `/specs/001-alert-investigation-harness/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, contracts/tools.md, quickstart.md

**Tests**: INCLUDED — Constitution Principle VI makes security tests mandatory release gates; each story includes acceptance, negative, and (where relevant) adversarial tests written before implementation.

**Organization**: Tasks are grouped by user story (US1–US8 from spec.md) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US8)

## Path Conventions

Single project per plan.md: `src/harness/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create Python project skeleton (`pyproject.toml` with FastAPI, Pydantic v2, SQLAlchemy 2.x, litellm, structlog, pytest, httpx, alembic; pinned versions) and package tree `src/harness/{api,orchestrator,policy,tools,connectors,evidence,analysis,model,report,audit,storage,config,cli}/__init__.py` plus `tests/{contract,unit,integration,adversarial,fixtures}/__init__.py`
- [X] T002 [P] Configure linting/formatting/type-checking (ruff, mypy strict) in `pyproject.toml` and add `env.example` with FAKE_MODEL, model/provider, and DB settings
- [X] T003 [P] Create settings module with hard-floor/ceiling-validated default budget limits (10 min, 50 tool ops, 500 items/5 MB evidence, 20 model calls, 2 retries; never disableable — FR-031, research R9) in `src/harness/config/settings.py`
- [X] T004 [P] Configure structlog with secret-redaction processors and correlation-ID propagation in `src/harness/config/logging.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by ALL user stories — schemas, storage, identity, policy engine skeleton, audit service, state machine frame

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create SQLAlchemy models for all data-model.md entities (InvestigationCase, CaseLink, EvidenceItem, Claim, ClaimEvidenceLink, Hypothesis, AffectedEntity, TimelineEvent, InvestigationReport, ResponseActionProposal, ToolOperation, AuthorizationDecision, BudgetLedger, AuditEvent, AnalystFeedback) in `src/harness/storage/models.py`
- [X] T006 Initialize alembic and generate the initial migration in `alembic/` and `alembic.ini` *(deviation: schema managed via SQLAlchemy `create_all` for the SQLite dev/eval environment; alembic deferred to the PostgreSQL pilot — documented in docs/harness.md and src/harness/storage/db.py)*
- [X] T007 Implement case-scoped repository layer requiring explicit `CaseContext` on every query (mandatory case_id filter; cross-case reads structurally impossible — FR-003, research R12) in `src/harness/storage/repositories.py`
- [X] T008 [P] Create Pydantic domain schemas (case, evidence, claim, hypothesis, report content with all FR-013 sections, budget limits, tool I/O envelopes) in `src/harness/storage/schemas.py`
- [X] T009 [P] Implement stub identity provider issuing/verifying signed JWTs with analyst ID + data-source claims behind an `IdentityProvider` interface (research R7) in `src/harness/api/identity.py`
- [X] T010 Implement AuditService: append-only writes, per-case sequence, SHA-256 hash chaining (`prev_hash`/`event_hash`), all FR-028 event types, no update/delete path (FR-030, research R5) in `src/harness/audit/service.py`
- [X] T011 Implement PolicyEngine (single PEP): deny-by-default `authorize(agent_identity, analyst_claims, case_scope, operation, target_resource, budget_snapshot)` returning recorded AuthorizationDecision; absence/ambiguity → deny; denial reasons never reveal resource existence (FR-018, FR-019, FR-022) in `src/harness/policy/engine.py`
- [X] T012 Implement BudgetLedger service enforcing all five limits with atomic consumption checks and `budget_consumed` audit events (FR-031) in `src/harness/orchestrator/budget.py`
- [X] T013 Implement deterministic state-machine framework: state enum (12 workflow + 8 terminal states per data-model.md), transition table, per-state config (input/output schema, permitted tools, entry/exit conditions, max retries, timeout, failure transition), terminal-state→case-status mapping, `state_transition` audit events (Constitution V) in `src/harness/orchestrator/machine.py`
- [X] T014 Implement static ToolRegistry loading the five contracts/tools.md tool definitions (name, version, operation, I/O schemas, authorization_scope, timeout, max_result_bytes, error classification); no runtime registration (FR-021) in `src/harness/tools/registry.py`
- [X] T015 Implement tool invoker: every call → PolicyEngine check → budget check → connector execution with timeout/size enforcement → ToolOperation persistence + `tool_requested`/`authorization_decision`/`tool_result`/`tool_failure` audit events; denial is authoritative, no alternative probing (FR-022–FR-024) in `src/harness/tools/invoker.py`
- [X] T016 [P] Create the three synthetic read-only connectors (alert source, endpoint telemetry, identity/asset context) backed by fixture data in `src/harness/connectors/alert_source.py`, `src/harness/connectors/endpoint_telemetry.py`, `src/harness/connectors/identity_context.py`
- [X] T017 [P] Create synthetic fixture corpus: normal alerts (ALERT-1001 etc.), related events, endpoint telemetry, identity/asset records in `tests/fixtures/synthetic_corpus.py`
- [X] T018 [P] Implement ModelGateway behind narrow interface (litellm + deterministic FakeModel for tests; model/config version pinned and audited — research R3) in `src/harness/model/gateway.py`
- [X] T019 Create FastAPI app factory with bearer-token auth middleware, error envelope (`{"error":{code,message}}`), 403-safe responses, and router mounting in `src/harness/api/app.py`
- [X] T020 [P] Foundational unit tests: policy engine deny-by-default/ambiguity-denial, budget enforcement, state-machine transitions, repository case-scoping, audit hash chain in `tests/unit/test_policy.py`, `tests/unit/test_budget.py`, `tests/unit/test_machine.py`, `tests/unit/test_repositories.py`, `tests/unit/test_audit_chain.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Create and investigate a single alert (Priority: P1) 🎯 MVP

**Goal**: Authenticated analyst starts an investigation from one alert (selected or submitted) and receives a structured, evidence-backed report from an isolated case.

**Independent Test**: POST /cases with a synthetic alert; verify isolated case creation and a complete report containing all FR-013 sections, every material claim evidence-linked or explicitly labeled.

### Tests for User Story 1 (write first, ensure they FAIL)

- [X] T021 [P] [US1] Contract tests for POST /cases, GET /cases/{id}, GET /cases/{id}/report (schemas, 400/403 paths, both intake origins) in `tests/contract/test_cases_api.py`
- [X] T022 [P] [US1] Contract tests validating report JSON against the FR-013 section schema in `tests/contract/test_report_schema.py`
- [X] T023 [P] [US1] Integration test: end-to-end investigation of ALERT-1001 with FakeModel → completed case, full report, timeline ordered, entities extracted, inconclusive labeling when evidence insufficient (spec scenarios 1, 3, 9) in `tests/integration/test_investigation_flow.py`

### Implementation for User Story 1

- [X] T024 [US1] Implement case lifecycle service: create case (unique ID, both intake origins, analyst-submitted content labeled `analyst_provided`/untrusted, limit-override validation, re-runs create new isolated cases — FR-001/FR-002) in `src/harness/orchestrator/case_service.py`
- [X] T025 [P] [US1] Implement evidence store service: verbatim persistence with full provenance (source, source_record_id, collected_at, event_at, trust_classification, transformation_history — FR-006/FR-008) in `src/harness/evidence/store.py`
- [X] T026 [P] [US1] Implement analysis services: timestamp-ordered timeline builder and entity extractor (users, endpoints, applications, IPs, processes, files — FR-014, deterministic code) in `src/harness/analysis/timeline.py` and `src/harness/analysis/entities.py`
- [X] T027 [US1] Implement claim/hypothesis service: model-assisted hypothesis generation via ModelGateway, claim typing (observation/correlation/inference/analyst-provided/unverified), evidence linking, inconclusive-over-fabrication rule (FR-007, FR-009–FR-011, FR-015) in `src/harness/analysis/claims.py`
- [X] T028 [US1] Implement the concrete workflow states RECEIVE_ALERT → … → COMPLETE wiring case service, tool invoker, evidence store, analysis, and report generation into the state machine in `src/harness/orchestrator/states.py`
- [X] T029 [US1] Implement report generator producing schema-valid report content (all FR-013 sections) plus output verifier (claim-evidence completeness check, secret-pattern scan — FR-035) in `src/harness/report/generator.py` and `src/harness/report/verifier.py`
- [X] T030 [US1] Implement API routers POST /cases, GET /cases/{id}, GET /cases/{id}/report (JSON + Markdown rendering) in `src/harness/api/routes_cases.py` and `src/harness/api/routes_reports.py`
- [X] T031 [US1] Implement CLI entry points `issue-token` and `investigate` per quickstart.md in `src/harness/cli/__main__.py`

**Checkpoint**: MVP — a full investigation runs end-to-end and all US1 tests pass

---

## Phase 4: User Story 2 - Inspect evidence provenance (Priority: P1)

**Goal**: Analyst selects any material finding and inspects supporting/contradicting/missing evidence with full provenance metadata.

**Independent Test**: Complete an investigation, GET /cases/{id}/claims/{claim_id}/evidence, verify provenance fields and relationship labels; verify inference never presented as direct observation.

### Tests for User Story 2

- [X] T032 [P] [US2] Contract test for GET /cases/{id}/claims/{claim_id}/evidence (response schema, 403-safe unknown claim) in `tests/contract/test_provenance_api.py`
- [X] T033 [P] [US2] Integration test: material conclusion → provenance display with source/event IDs, timestamps, trust classification; correlation/inference distinguished from observation (spec scenarios US2-1..3) in `tests/integration/test_provenance.py`

### Implementation for User Story 2

- [X] T034 [US2] Implement provenance query service assembling claim + linked evidence (supports/contradicts/inconclusive) + missing-evidence statement (FR-012) in `src/harness/evidence/provenance.py`
- [X] T035 [US2] Implement API route GET /cases/{case_id}/claims/{claim_id}/evidence in `src/harness/api/routes_evidence.py`

**Checkpoint**: US1 + US2 independently functional

---

## Phase 5: User Story 3 - Enforce read-only operation (Priority: P1)

**Goal**: Every response/destructive/administrative/arbitrary-command operation is denied outside the model; response actions surface only as proposals.

**Independent Test**: Drive the tool invoker with each prohibited operation and confirm denial, no state change, and audit recording; verify report contains proposals with impact/risk/rollback and no executed action.

### Tests for User Story 3

- [X] T036 [P] [US3] Unit tests: policy engine denies every FR-017 prohibited operation class; denial recorded; unauthorized-source denial reveals nothing (spec scenarios 6–7) in `tests/unit/test_readonly_enforcement.py`
- [X] T037 [P] [US3] Adversarial tests: tool-argument manipulation, privilege-escalation probing after denial, attempts to invoke unregistered tools (Constitution VI) in `tests/adversarial/test_privilege_escalation.py`
- [X] T038 [P] [US3] Integration test: investigation producing a ResponseActionProposal → proposal appears in report with affected resources, evidence, impact, risk, rollback; nothing executed (FR-016) in `tests/integration/test_response_proposals.py`

### Implementation for User Story 3

- [X] T039 [US3] Implement prohibited-operation policy rules (explicit deny list + default deny for any non-registered operation) with reason codes in `src/harness/policy/rules.py`
- [X] T040 [US3] Implement ResponseActionProposal generation in the analysis/report pipeline (proposal-only, FR-016) in `src/harness/analysis/proposals.py`

**Checkpoint**: Read-only guarantee test suite is a passing release gate

---

## Phase 6: User Story 4 - Produce a complete audit trail (Priority: P1)

**Goal**: An authorized reviewer reconstructs the full investigation from ordered, tamper-evident audit records the agent cannot modify.

**Independent Test**: Run an investigation, GET /cases/{id}/audit and /audit/verify; confirm every FR-028 event type present, ordering correct, hash chain intact, and no agent mutation path.

### Tests for User Story 4

- [X] T041 [P] [US4] Contract tests for GET /cases/{id}/audit and GET /cases/{id}/audit/verify in `tests/contract/test_audit_api.py`
- [X] T042 [P] [US4] Audit-completeness integration test: reconstruct a completed investigation's sequence (data access, policy decisions, tool ops, findings, feedback) from audit alone; every tool op has case ID, agent identity, decision, timestamp (FR-029, spec scenario 12) in `tests/integration/test_audit_completeness.py`
- [X] T043 [P] [US4] Adversarial tests: attempts to suppress/alter audit records via any code path fail and raise a `security_event` (Constitution VII) in `tests/adversarial/test_audit_tamper.py`

### Implementation for User Story 4

- [X] T044 [US4] Implement reviewer audit API routes GET /cases/{case_id}/audit (filtering, pagination) and GET /cases/{case_id}/audit/verify (chain recomputation) in `src/harness/api/routes_audit.py`
- [X] T045 [US4] Wire remaining audit emission points across orchestrator/tools/report (ensure all 18 FR-028 event types emitted; add `security_event` on tamper/manipulation attempts) in `src/harness/audit/emitters.py`

**Checkpoint**: Full reconstruction from audit records demonstrated

---

## Phase 7: User Story 5 - Resist instructions in untrusted evidence (Priority: P1)

**Goal**: Instructions embedded in any retrieved content are inert data; manipulation attempts are recorded.

**Independent Test**: Investigate hostile fixtures (exfiltration instruction, command request, permission grant); verify objective/permissions/tools unchanged and `manipulation_detected` audit events emitted.

### Tests for User Story 5

- [X] T046 [P] [US5] Create hostile-content fixture corpus (ALERT-INJ-01 etc.: ignore-policy/exfiltrate text, command-execution requests, permission grants, tool-selection injections, audit-alteration requests, secret requests) in `tests/fixtures/hostile_corpus.py`
- [X] T047 [P] [US5] Adversarial tests: direct + indirect prompt injection preserve objective, tool set, permissions, and audit; manipulation recorded (spec scenarios 4–5, US5-1..3) in `tests/adversarial/test_prompt_injection.py`
- [X] T048 [P] [US5] Unit tests for the instruction-pattern detector (true/false positive cases) in `tests/unit/test_instruction_detector.py`

### Implementation for User Story 5

- [X] T049 [US5] Implement deterministic instruction-pattern detector flagging evidence (`manipulation_flag`) and emitting `manipulation_detected` audit events (FR-027, research R6) in `src/harness/evidence/instruction_detector.py`
- [X] T050 [US5] Implement prompt assembly with structural untrusted-content demarcation (evidence never in system prompts; model has no direct tool access — FR-025/FR-026) in `src/harness/model/prompts.py`

**Checkpoint**: Adversarial injection suite is a passing release gate

---

## Phase 8: User Story 6 - Provide analyst feedback (Priority: P2)

**Goal**: Analyst rates the investigation, corrects findings, flags irrelevant evidence, records disposition — case-scoped only.

**Independent Test**: POST /cases/{id}/feedback after a report; verify persistence against the case, audit `feedback_recorded` event, and absence from any other case.

### Tests for User Story 6

- [X] T051 [P] [US6] Contract test for POST /cases/{id}/feedback (schema, rating enum, 403/409 paths) in `tests/contract/test_feedback_api.py`
- [X] T052 [P] [US6] Integration test: feedback recorded and case-isolated (spec scenarios US6-1..2) in `tests/integration/test_feedback.py`

### Implementation for User Story 6

- [X] T053 [US6] Implement feedback service (FR-034) in `src/harness/analysis/feedback.py`
- [X] T054 [US6] Implement API route POST /cases/{case_id}/feedback and case-link route POST /cases/{case_id}/links (explicit linking, FR-003) in `src/harness/api/routes_feedback.py`

**Checkpoint**: Feedback loop complete

---

## Phase 9: User Story 7 - Stop safely on budget exhaustion (Priority: P2)

**Goal**: Any limit breach or cancellation stops the workflow safely and yields a partial report with the exact termination reason.

**Independent Test**: Run with `--max-tool-operations 3`; verify `budget_exhausted` status, partial report describing completed work + unavailable evidence + reason; verify cancel endpoint mid-run.

### Tests for User Story 7

- [X] T055 [P] [US7] Integration tests: each of the five limits triggers safe stop + partial report + exact termination reason (spec scenario 10); tool failure → unavailable evidence identified, no unauthorized substitution (spec scenario 8) in `tests/integration/test_budget_exhaustion.py`
- [X] T056 [P] [US7] Integration test: POST /cases/{id}/cancel mid-run → safe stop, partial report, `cancelled` status (clarification Q1) in `tests/integration/test_cancellation.py`
- [X] T057 [P] [US7] Unit tests: failure transitions map to correct terminal states; failures never expand authorization (FR-020, FR-033) in `tests/unit/test_fail_safe.py`

### Implementation for User Story 7

- [X] T058 [US7] Implement partial-report generation on any terminal path (completed work, unavailable evidence, termination reason — FR-032) in `src/harness/report/partial.py`
- [X] T059 [US7] Implement cancellation: POST /cases/{case_id}/cancel route + orchestrator cooperative cancel check between states in `src/harness/api/routes_cases.py` and `src/harness/orchestrator/machine.py`

**Checkpoint**: All terminal paths produce useful, audited partial results

---

## Phase 10: User Story 8 - Compare hypotheses (Priority: P2)

**Goal**: Report lists alternative hypotheses with the evidence that would confirm or reject each.

**Independent Test**: Investigate a multi-explanation fixture alert; verify the report's hypotheses section lists alternatives with confirming/rejecting evidence needs and evaluation status.

### Tests for User Story 8

- [X] T060 [P] [US8] Integration test: multi-explanation alert → alternative hypotheses with confirming/rejecting evidence identified (spec scenario US8-1) in `tests/integration/test_hypotheses.py`

### Implementation for User Story 8

- [X] T061 [US8] Extend hypothesis service with alternative-hypothesis comparison and confirming/rejecting evidence-needs fields feeding the report section (FR-015) in `src/harness/analysis/hypotheses.py`

**Checkpoint**: All eight user stories independently functional

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Remaining release-gate suites, hardening, documentation

- [X] T062 [P] Adversarial tests: secret-extraction attempts (from connectors, prompts, logs, reports) never disclose secrets (FR-035, SC-005) in `tests/adversarial/test_secret_extraction.py`
- [X] T063 [P] Adversarial tests: cross-case data access attempts fail through every API and service path (spec scenario 11) in `tests/adversarial/test_case_isolation.py`
- [X] T064 [P] Adversarial tests: malformed/malicious tool responses, oversized evidence, endless-execution attempts handled safely (FR-033) in `tests/adversarial/test_malformed_inputs.py`
- [X] T065 [P] Contract test asserting the absence of prohibited endpoints (audit mutation, action execution, runtime tool registration) in `tests/contract/test_absent_endpoints.py`
- [X] T066 Verify every FR-001–FR-035 maps to at least one passing test (traceability matrix, Constitution I) in `tests/test_traceability.py`
- [X] T067 [P] Write README for the harness (architecture overview, safety model, how to run) in `docs/harness.md`
- [X] T068 Run full quickstart.md validation end-to-end (service, CLI, safety demos) and fix discrepancies
- [X] T069 Add Dockerfile + compose for dev/evaluation environments in `Dockerfile` and `docker-compose.yml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: After Foundational; no story dependencies — MVP
- **US2 (Phase 4)**: After US1 (needs claims + evidence from completed investigations)
- **US3 (Phase 5)**: After Foundational; independent of US1 for policy tests; proposal reporting (T038, T040) needs US1's report pipeline
- **US4 (Phase 6)**: After US1 (needs a full run to audit); audit service itself exists from Phase 2
- **US5 (Phase 7)**: After US1 (needs the evidence/model pipeline)
- **US6 (Phase 8)**: After US1 (needs completed reports)
- **US7 (Phase 9)**: After US1 (needs the workflow to bound)
- **US8 (Phase 10)**: After US1 (extends hypothesis service)
- **Polish (Phase 11)**: After all desired stories

### Within Each User Story

Tests written first and failing → models/services → endpoints → integration. Safety suites (T036–T037, T043, T047, T062–T064) are binary release gates.

### Parallel Opportunities

- Phase 1: T002, T003, T004 in parallel after T001
- Phase 2: T008, T009, T016, T017, T018 in parallel once T005–T007 done; T020 tests parallel at phase end
- After US1: US2, US3(remainder), US4, US5, US6, US7, US8 can proceed in parallel (different files/services)
- All `[P]` test tasks within a story can run together

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (must fail first):
Task: "Contract tests for cases API in tests/contract/test_cases_api.py"
Task: "Contract tests for report schema in tests/contract/test_report_schema.py"
Task: "Integration test investigation flow in tests/integration/test_investigation_flow.py"

# Then parallel services:
Task: "Evidence store in src/harness/evidence/store.py"
Task: "Timeline/entities in src/harness/analysis/timeline.py, entities.py"
```

## Implementation Strategy

### MVP First (US1)

1. Phases 1–2 (setup + foundational safety core: policy, audit, budgets, state machine)
2. Phase 3 (US1) → validate independently → demo end-to-end investigation
3. Note: even the MVP passes through the deny-by-default policy engine and audit trail, since those are foundational

### Incremental Delivery

Each subsequent story (US2–US8) is an independently testable increment; P1 stories (US2–US5) before P2 stories (US6–US8). Release requires all adversarial/safety suites green (Gate 6) — they are never averaged into a quality score.

## Notes

- [P] = different files, no incomplete dependencies
- Every FR is traceable to tasks/tests (enforced by T066)
- Stop at any checkpoint to validate the story independently
