# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

**skekOk** ("the Scroll-Keeper") is a read-only, evidence-driven cybersecurity
agent harness for SOC single-alert investigation. The implemented feature is
`001-alert-investigation-harness`.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/001-alert-investigation-harness/plan.md`

Active feature: `specs/001-alert-investigation-harness/` (spec.md, plan.md,
research.md, data-model.md, contracts/, quickstart.md, tasks.md — all 69 tasks
implemented).
Stack: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x (SQLite dev),
litellm (optional), structlog, pytest. Deterministic hand-rolled state machine;
no agent framework. Governance: `.specify/memory/constitution.md`.
<!-- SPECKIT END -->

## Layout

```
src/harness/
├── api/            # FastAPI routers, JWT identity (dev stub)
├── orchestrator/   # State machine, case service, workflow states, budgets
├── policy/         # Policy engine (deny-by-default PEP) + prohibited-op rules
├── tools/          # Static tool registry + authorized invoker
├── connectors/     # 3 synthetic read-only sources + fixtures
├── evidence/       # Evidence store, provenance, instruction detector
├── analysis/       # Timeline, entities, claims/hypotheses, proposals, feedback
├── model/          # Model gateway (FakeModel / litellm) + demarcated prompts
├── report/         # Report generator + output verifier (secret scan)
├── audit/          # Append-only hash-chained audit service
├── storage/        # SQLAlchemy models, case-scoped repositories, schemas
├── config/         # Settings (budget limits), structlog with redaction
└── cli/            # issue-token, investigate

tests/              # contract / unit / integration / adversarial / fixtures
docs/harness.md     # Architecture and safety model
```

## Commands

```bash
source .venv/bin/activate
pip install -e ".[dev]"                    # install
pytest tests -q                            # full suite (172 tests)
pytest tests/adversarial -q                # safety release gates (must be 100%)
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice
uvicorn 'harness.api.app:get_app' --factory
```

## Non-negotiable rules (from the constitution)

1. **Constitution first** — `.specify/memory/constitution.md` overrides
   everything; the spec overrides the plan; the plan overrides code.
2. **Read-only** — never add response/destructive/administrative capabilities,
   mutation endpoints (PUT/PATCH/DELETE), runtime tool registration, shell
   execution, or arbitrary HTTP egress. `tests/contract/test_absent_endpoints.py`
   enforces this.
3. **The model is never a policy enforcement point** — authorization, budgets,
   validation, and audit happen in deterministic code. The model has no tool
   access; its output is untrusted and schema-validated.
4. **Deny by default** — absence or ambiguity of an authorization input means
   deny. Denials are opaque (never reveal whether data exists) and recorded.
5. **Audit is append-only** — never add update/delete paths to
   `AuditEvent`/`AuditService`; keep the hash chain canonicalization stable.
6. **Case isolation** — all case-scoped data access goes through
   `CaseScopedRepository` with an explicit `CaseContext`. No durable
   cross-case memory of any kind.
7. **Evidence integrity** — persist retrieved content verbatim with full
   provenance; never sanitize evidence; label claim types honestly
   (inference ≠ observation); prefer "inconclusive" over invention.
8. **Budgets always apply** — never allow limits to be disabled or unbounded
   (`BudgetLimits` hard bounds in `config/settings.py`).
9. **Safety tests are release gates** — adversarial suites must pass 100%,
   never averaged. New FRs require updating
   `tests/test_traceability.py`.
10. **No secrets** in prompts, code, logs, evidence, reports, or audit
    payloads — redaction lives in `config/logging.py`.

## Workflow

- Spec-driven (GitHub Spec Kit): changes to behavior require updating the
  spec/plan/tasks under `specs/…` first; implementation must not exceed the
  approved specification.
- Tests first for new behavior; every MUST requirement maps to at least one
  test (checked by `tests/test_traceability.py`).
- **Docs in the same change** (constitution Gate 5): every spec implementation
  must update the affected documents under `docs/` — architecture, workflow,
  safety model, data model, API/CLI, audit, configuration, testing,
  deployment — so `docs/` never contradicts implemented behavior.
- Use synthetic data only (`src/harness/connectors/fixtures.py`,
  `tests/fixtures/`).
