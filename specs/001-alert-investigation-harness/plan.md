# Implementation Plan: Read-Only Alert Investigation Harness

**Branch**: `001-alert-investigation-harness` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-alert-investigation-harness/spec.md`

## Summary

Build a read-only, evidence-driven agent harness that lets an authenticated SOC analyst investigate exactly one security alert and receive a structured, evidence-backed investigation report. The harness runs a deterministic state-machine workflow (per Constitution Principle V) around a single LLM-assisted investigation agent, with policy enforcement, tool authorization, budget enforcement, evidence provenance, case isolation, and an append-only audit trail all implemented in deterministic code outside the model. The MVP retrieves from at most three approved read-only mock/synthetic data sources, treats all retrieved content as hostile, and never executes response actions.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI (HTTP API), Pydantic v2 (schema validation & typed tool contracts), SQLAlchemy 2.x (persistence), litellm (narrow model-provider interface), structlog (structured logging). No agent framework — the workflow state machine is hand-rolled deterministic code (Constitution V, VIII).

**Storage**: SQLite for development/evaluation; schema kept PostgreSQL-compatible via SQLAlchemy for a later pilot. Append-only audit table with hash chaining for tamper evidence.

**Testing**: pytest + httpx test client; adversarial evaluation corpus as pytest fixtures (synthetic alerts with embedded hostile instructions); coverage of all Gate 6 test categories.

**Target Platform**: Linux server (containerized), non-production development environment and isolated evaluation environment only (no production connectivity in this feature).

**Project Type**: Single backend service (web API) + CLI entry point for local/evaluation runs. No frontend in this feature; the report and audit views are JSON/Markdown API responses.

**Performance Goals**: Median investigation completes within the default elapsed-time budget (10 minutes); report generation adds < 5 s over evidence collection; audit writes never dropped.

**Constraints**: Strictly read-only connectors; deny-by-default authorization; all limits enforceable and never disableable; no secrets in prompts, logs, or reports; model output never used as a policy decision.

**Scale/Scope**: Pilot scale — single tenant, ≤ 3 approved data sources, a limited set of agreed alert types, tens of concurrent investigations at most.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance |
|---|-----------|------------|
| I | Specification Before Implementation | PASS — approved spec.md with normative FRs; all MUSTs traceable to tasks/tests via FR IDs. |
| II | Defensive and Read-Only MVP | PASS — scope matches the constitutional MVP exactly; FR-016/FR-017 keep response actions as proposals; no autonomous actions. |
| III | Zero-Trust Agent Execution | PASS — every run gets execution ID, workload identity, initiating analyst, case ID, authorization context, tool allowlist, time/tool/cost limits, termination condition (FR-004, FR-021–FR-024, FR-031). Policy Enforcement Point (PEP) is deterministic code outside the model. Deny by default. |
| IV | Evidence-Driven Decisions | PASS — evidence model retains full provenance (FR-008); claim types distinguish observation/correlation/inference/analyst-provided/unverified (FR-009); inconclusive over fabrication (FR-011). |
| V | Deterministic Orchestration | PASS — explicit state machine with the constitutionally required states and terminal states; each state defines I/O schemas, permitted tools, retries, timeouts, failure transitions. No runtime-created sub-agents or tools. |
| VI | Security Testing Is Mandatory | PASS — testing strategy (below) covers all mandated positive, negative, authorization-denial, malformed-input, isolation, audit-completeness, and adversarial categories as release gates. |
| VII | Complete Observability | PASS — append-only, hash-chained audit trace with correlation IDs, versions, transitions, tool ops, authorization decisions, budgets, termination reason (FR-028–FR-030). Agent has no write path to audit mutation. |
| VIII | Simplicity and Minimal Scope | PASS — one supervisor workflow, one investigation agent, one policy layer, one evidence store, one append-only audit mechanism, one evaluation corpus; no multi-agent design; minimal pinned dependencies. |

**Post-Phase-1 re-check**: PASS — data model and contracts introduce no unspecified behavior; no exceptions required. Complexity Tracking is empty.

### Gate 3 required identifications

- **Trust boundaries**: (1) analyst ↔ API (authenticated); (2) orchestrator ↔ model (untrusted output, no authority); (3) orchestrator ↔ tools/connectors (typed, authorized per call); (4) retrieved evidence ↔ agent context (all evidence untrusted/hostile); (5) agent ↔ audit store (write-append only via audit service, never direct).
- **Component responsibilities**: API layer (authn, case lifecycle); Orchestrator (state machine, budgets, retries); Policy Engine (PEP — deny-by-default authorization of every tool call); Tool Registry (typed read-only tools); Connectors (≤3 approved read-only sources); Evidence Store (provenance-preserving, case-scoped); Claim/Hypothesis service; Report Generator; Audit Service (append-only); Model Gateway (narrow litellm interface, prompt assembly with untrusted-content demarcation).
- **Identities**: initiating analyst identity (from org identity system, stubbed via signed token in dev); agent workload identity (per-execution service identity); unique execution ID; case ID. Agents never reuse analyst credentials.
- **Data flows**: alert intake → validation → authorization → evidence retrieval (connectors → evidence store with provenance) → model-assisted analysis (evidence passed as demarcated untrusted data) → claims/hypotheses (linked to evidence IDs) → report → analyst review/feedback. All flows emit audit events.
- **Tool permissions**: static registry; each tool declares operation, target-resource scope, result-size limit, timeout; every invocation checked against agent identity + analyst authorization + case scope + operation + resource + remaining budget (FR-022).
- **Policy enforcement points**: single Policy Engine invoked by the orchestrator before every tool call and every state transition with side effects; also gates audit-view access and case linking.
- **Isolation mechanism**: case-scoped storage keys — every evidence, claim, context, and feedback row carries a case ID; queries are case-filtered at the repository layer; cross-case reads structurally impossible without explicit link records; no durable cross-case memory.
- **Secrets mechanism**: connector credentials held in environment/secret store, injected only into connector adapters; never present in model context, logs (structlog redaction processors), evidence, or reports; report/output secret-pattern scanner as a verification gate (FR-035).
- **Evidence model**: see data-model.md — EvidenceItem with source, source record ID, collection/event timestamps, trust classification, transformation history, claim links.
- **Audit model**: append-only AuditEvent table, hash-chained, correlation ID = execution ID; covers all FR-028 event types; agent has no mutation path.
- **Failure handling**: every failure maps to a constitutional terminal state (ACCESS_DENIED, INCOMPLETE_EVIDENCE, SOURCE_UNAVAILABLE, POLICY_BLOCKED, BUDGET_EXCEEDED, VALIDATION_FAILED, CANCELLED, SYSTEM_ERROR); partial report generated where work was completed; failures never expand authorization (FR-020, FR-032, FR-033).
- **Testing strategy**: contract tests from Pydantic schemas; unit tests for policy engine, budgets, state machine; integration tests over synthetic corpora; adversarial suite (prompt injection, tool-argument manipulation, secret extraction, cross-case access, audit-suppression attempts, endless-execution); isolation and audit-completeness tests. Safety tests are binary release gates.
- **Deployment and rollback**: containerized service; dev + isolated evaluation environments only; configuration-pinned model version; rollback = redeploy previous image + config; no production data connectivity in this feature (shadow mode is a later feature).

## Project Structure

### Documentation (this feature)

```text
specs/001-alert-investigation-harness/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── api.md           # HTTP API contract
│   └── tools.md         # Registered tool contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/harness/
├── api/                 # FastAPI routers: cases, reports, evidence, audit, feedback
├── orchestrator/        # Deterministic state machine, state definitions, budgets, retries
├── policy/              # Policy engine (PEP), authorization context, decisions
├── tools/               # Tool registry + typed read-only tool adapters
├── connectors/          # ≤3 approved read-only source connectors (synthetic/mock for MVP)
├── evidence/            # Evidence store, provenance, trust classification
├── analysis/            # Claims, hypotheses, timeline, entity extraction
├── model/               # Model gateway (litellm), prompt assembly, untrusted-content demarcation
├── report/              # Report generator + output verifier (secret scan, claim-evidence check)
├── audit/               # Append-only audit service, hash chaining, reviewer views
├── storage/             # SQLAlchemy models, case-scoped repositories
├── config/              # Limits/budget defaults, settings
└── cli/                 # Local/evaluation entry point

tests/
├── contract/            # Schema & API contract tests
├── unit/                # Policy, budgets, state machine, provenance
├── integration/         # End-to-end synthetic investigations
├── adversarial/         # Injection, escalation, secret-extraction, isolation attacks
└── fixtures/            # Synthetic alerts, evidence corpora, hostile-content corpus
```

**Structure Decision**: Single Python backend service (`src/harness/`) with a five-tier test tree. This is the smallest architecture satisfying Constitution VIII: one workflow, one agent, one policy layer, one evidence store, one audit mechanism.

## Complexity Tracking

No constitutional violations. No exceptions required.
