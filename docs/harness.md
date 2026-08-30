# Alert Investigation Harness — Overview

A read-only, evidence-driven agent harness that assists SOC analysts with
investigating a single security alert. Implements
`specs/001-alert-investigation-harness/spec.md` under the project constitution.

> This page is the high-level overview. The full documentation set starts at
> the [documentation index](index.md) — architecture, workflow, safety model, data
> model, API/CLI references, audit, configuration, testing, and deployment.

## Architecture

```
Analyst ──HTTP+JWT──▶ FastAPI (src/harness/api)
                        │
                        ▼
              Orchestrator state machine        ◀── deterministic, Constitution V
              (src/harness/orchestrator)
                │           │            │
                ▼           ▼            ▼
          Policy Engine  Budget      Model Gateway ── model has NO tools,
          (deny-by-      Ledger      (fake/litellm)   output = untrusted data
           default PEP)
                │
                ▼
          Tool Invoker ──▶ Static Tool Registry (5 read-only ops)
                │              │
                ▼              ▼
          Audit Service   3 synthetic connectors
          (append-only,   (alert_source, endpoint_telemetry,
           hash-chained)   identity_context)
                │
                ▼
          SQLite (case-scoped repositories — cross-case reads impossible)
```

## Safety model

- **Read-only**: no response/destructive/administrative operation exists;
  the policy engine denies every prohibited operation class and any
  unregistered operation by default (FR-017–FR-021).
- **Zero trust**: every tool call is authorized against agent identity,
  analyst claims, case scope, operation, target, and budget — outside the
  model (FR-022–FR-023). Denials are opaque (FR-019) and authoritative.
- **Untrusted content**: all retrieved evidence is treated as hostile; it is
  demarcated as data in prompts, the model cannot invoke tools, and an
  instruction-pattern detector records manipulation attempts (FR-025–FR-027).
- **Budgets**: safe defaults for time/tools/evidence/model-calls/retries
  always apply and cannot be disabled; exhaustion stops safely with a partial
  report (FR-031–FR-032).
- **Audit**: append-only, hash-chained per-case audit trail; reviewers can
  verify chain integrity via the API (FR-028–FR-030).
- **Isolation**: case-scoped repositories make cross-case reads structurally
  impossible; no durable cross-case memory exists (FR-003, FR-005).

## Run

See `specs/001-alert-investigation-harness/quickstart.md`. Short version:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m harness.cli issue-token --analyst alice --sources alert_source,endpoint_telemetry,identity_context
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice
uvicorn 'harness.api.app:get_app' --factory   # HTTP API
```

## Tests

```bash
pytest tests/contract tests/unit      # fast gates
pytest tests/integration              # end-to-end synthetic investigations
pytest tests/adversarial              # safety release gates (must be 100%)
pytest tests/test_traceability.py     # FR -> test mapping
```

Safety suites are binary release gates (Constitution VI) — never averaged.

## Notes / deviations

- Schema is created via SQLAlchemy `create_all` for the SQLite dev/eval
  environment; alembic migrations are introduced with the PostgreSQL pilot.
- The API runs investigations synchronously (deterministic synthetic
  sources); background execution arrives with the production pilot feature.
- Cross-tenant isolation tests are N/A: the MVP is single-tenant (plan.md).
