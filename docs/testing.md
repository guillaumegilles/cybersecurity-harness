# Testing

Per Constitution Principle VI, security tests are **mandatory release
gates** — a single safety failure blocks release; results are never averaged
into a quality score.

## Suites

```bash
pytest tests -q                       # everything (172 tests)
pytest tests/contract -q              # API & schema contracts
pytest tests/unit -q                  # policy, budgets, state machine, isolation, audit chain
pytest tests/integration -q           # end-to-end synthetic investigations
pytest tests/adversarial -q           # attack scenarios — release gates
pytest tests/test_traceability.py -q  # FR → test mapping
```

| Suite | Files | Focus |
|---|---|---|
| `contract/` | `test_cases_api`, `test_report_schema`, `test_provenance_api`, `test_audit_api`, `test_feedback_api`, `test_absent_endpoints` | Request/response schemas, error semantics (400/401/403/409/422), all 20 FR-013 report sections, **absence** of prohibited endpoints and mutation methods |
| `unit/` | `test_policy`, `test_budget`, `test_machine`, `test_repositories`, `test_audit_chain`, `test_readonly_enforcement`, `test_instruction_detector`, `test_fail_safe` | Deny-by-default over every prohibited operation class, hard-bounded budgets, transition-table integrity, structural case isolation, hash-chain tamper detection, detector precision |
| `integration/` | `test_investigation_flow`, `test_provenance`, `test_response_proposals`, `test_audit_completeness`, `test_feedback`, `test_budget_exhaustion`, `test_cancellation`, `test_hypotheses` | Full investigations over synthetic corpora; provenance end-to-end; partial reports with exact termination reasons; audit-only reconstruction |
| `adversarial/` | `test_prompt_injection`, `test_privilege_escalation`, `test_audit_tamper`, `test_secret_extraction`, `test_case_isolation`, `test_malformed_inputs` | See coverage table below |

## Adversarial coverage (Constitution VI)

| Mandated category | Test |
|---|---|
| Direct prompt injection | `test_prompt_injection` (analyst-submitted hostile content) |
| Indirect prompt injection in retrieved evidence | `test_prompt_injection` (ALERT-INJ-01) |
| Malicious instructions in logs/documents | `test_prompt_injection`, `test_instruction_detector` |
| Attempted privilege escalation | `test_privilege_escalation` (post-denial probing) |
| Tool-argument manipulation | `test_privilege_escalation` |
| Malicious or malformed tool responses | `test_malformed_inputs` (non-dict results, oversized payloads) |
| Secret extraction | `test_secret_extraction` (planted fixture secret) |
| Unauthorized network communication | structural — no egress capability; asserted via tool-set checks in `test_prompt_injection` |
| Memory poisoning | `test_malformed_inputs` (no durable memory store; stateless gateway) |
| Cross-case data access | `test_case_isolation` |
| Cross-tenant data access | N/A — single-tenant MVP (documented scope) |
| Audit suppression/alteration requests | `test_audit_tamper` (service API, DB edit, DB deletion) |
| Unsupported conclusions | `test_malformed_inputs` (hostile model output degrades to inconclusive) |
| Fabricated evidence | claim-evidence completeness in verifier + `test_provenance` |
| Repeated or replayed operations | `test_malformed_inputs` (1000-fold replay stopped by budget) |
| Excessive/endless agent execution | budget + retry tests |

## Test infrastructure

- **Fresh database per test** — `tests/conftest.py` provides `db`/`session`
  (direct SQLAlchemy) and `client` (FastAPI `TestClient` with its own SQLite
  file) fixtures.
- **Deterministic model** — `FakeModel` produces stable hypothesis JSON from
  structural features of the evidence, so integration tests are reproducible
  with no network or provider dependency.
- **Synthetic corpora** — `tests/fixtures/synthetic_corpus.py` (normal
  alerts, telemetry, identities — shared with the connectors) and
  `tests/fixtures/hostile_corpus.py` (injection strings and the hostile alert
  fixture).
- **Connector fault injection** — each connector exposes an `AVAILABLE`
  toggle for unavailable-dependency scenarios.

## Traceability (Constitution I)

`tests/test_traceability.py` maintains an explicit FR → test-file matrix and
fails if:

- any FR (FR-001…FR-035, FR-005a) is missing from the matrix,
- any mapped test file does not exist.

When adding a functional requirement to the spec, extend the matrix in the
same change.

## Writing new tests — conventions

1. **Safety first**: any new capability needs its negative tests
   (denial, failure, isolation) in the same PR as the positive path.
2. **Test through public seams**: the HTTP API or service entry points — not
   private helpers.
3. **Hostile fixtures live in** `tests/fixtures/hostile_corpus.py`; extend it
   rather than embedding attack strings inline.
4. **Never weaken a gate**: adversarial tests may be added, not relaxed,
   without a constitutional exception.
