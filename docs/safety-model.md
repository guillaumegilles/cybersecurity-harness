# Safety Model

The harness's safety guarantees are the product. This document explains each
guarantee, how it is enforced, and which tests prove it.

## 1. Strictly read-only operation (FR-016–FR-020)

**Guarantee.** The agent cannot isolate endpoints, disable accounts, revoke
credentials, delete/quarantine messages, block IPs/domains/files/processes,
modify detection rules or policies, create firewall rules, execute commands,
upload data externally, install tools, or create sub-agents. Response actions
appear only as **proposals** with affected resources, evidence, impact, risk,
and rollback method.

**Enforcement — three independent layers:**

1. *Capability absence*: no connector, tool, or endpoint implementing any
   response action exists in the codebase. The API surface has no
   PUT/PATCH/DELETE methods at all.
2. *Explicit deny list*: `policy/rules.py` enumerates every prohibited
   operation class from FR-017; the Policy Engine denies them regardless of
   registration.
3. *Default deny*: any operation not in the static registry — and not
   permitted by the current workflow state — is denied.

**Proof:** `tests/unit/test_policy.py` (parametrized over every prohibited
class), `tests/unit/test_readonly_enforcement.py`,
`tests/contract/test_absent_endpoints.py`,
`tests/integration/test_response_proposals.py`.

## 2. Zero-trust tool authorization (FR-021–FR-024)

**Guarantee.** Every tool operation is checked before execution against six
inputs: agent execution identity, analyst source claims, case scope, operation
registration (∩ state permission), target resource, and remaining budget.
Absence or ambiguity of any input means **deny**. Denials are authoritative —
the orchestrator never probes alternatives or substitutes sources.

**Enforcement.** `PolicyEngine.authorize()` is the single PEP, invoked by the
tool invoker for every call. It runs in deterministic code the model cannot
reach; the model cannot even request a tool. Each decision is persisted as an
`AuthorizationDecision` row and audited.

**Opaque denials (FR-019).** Denial reasons are fixed codes
(`not_authorized`, `operation_not_registered`, …) that never reveal whether
the requested data exists. The HTTP API mirrors this: missing and unauthorized
resources both return an identical `403`.

**Proof:** `tests/unit/test_policy.py`,
`tests/adversarial/test_privilege_escalation.py` (post-denial probing,
argument manipulation, unregistered names including injection strings).

## 3. Untrusted-content handling / prompt-injection resistance (FR-025–FR-027)

**Guarantee.** Instructions embedded in any retrieved content (alerts, logs,
documents, tool responses, analyst-submitted material) cannot change the
investigation objective, permissions, policies, tool set, or audit records.
Detected attempts are recorded.

**Enforcement — layered, none relying on the model:**

| Layer | Mechanism |
|---|---|
| Structural | The model **has no tools**. Tool use happens in orchestrator states; injected "tool calls" are inert text. |
| Prompt hygiene | Evidence enters only the user prompt, inside `<untrusted-evidence>` delimiters with an explicit data-not-instructions framing. Evidence never touches system prompts. |
| Detection | A deterministic pattern detector flags instruction-like content, sets `manipulation_flag` on the evidence item, and emits a `manipulation_detected` audit event. |
| Output validation | Model output is parsed and schema-validated; invalid evaluations/confidences degrade to `inconclusive`; "supported" claims without direct evidence are downgraded. |
| Output gate | The report verifier scans for secrets and unsupported claims before delivery. |

Evidence is stored **verbatim** — hostile content is preserved as evidence
with provenance, never sanitized away.

**Proof:** `tests/adversarial/test_prompt_injection.py` (hostile fixture
alert ALERT-INJ-01: exfiltration instruction, command request, permission
grant), `tests/unit/test_instruction_detector.py`,
`tests/adversarial/test_malformed_inputs.py` (hostile *model* output).

## 4. Evidence integrity and honest claims (FR-006–FR-015)

**Guarantee.** Every material claim links to evidence or is explicitly
labeled `unsupported` / `inferred` / `inconclusive`. Claim types distinguish
direct observation, correlation, inference, analyst-provided, and unverified
external information. Inference is never presented as observed fact. Missing
evidence is stated, never fabricated.

**Enforcement.**

- Direct-observation claims are generated *deterministically* from evidence
  carrying source record IDs — the model plays no part.
- Model-derived claims are always typed `inference`.
- The linkage rule in `analysis/claims.py`: a "supported" inference with no
  direct-observation evidence to link degrades to `inconclusive`.
- The output verifier fails the report if any supported material claim lacks
  evidence links.

**Proof:** `tests/integration/test_provenance.py`,
`tests/integration/test_investigation_flow.py`,
`tests/contract/test_report_schema.py`.

## 5. Operational limits (FR-031–FR-032)

**Guarantee.** Five per-investigation limits — elapsed time, tool operations,
evidence items/bytes, model calls, retries per operation — always apply.
Safe defaults exist, deployments may override them, but limits can never be
disabled or set outside hard bounds. Exhaustion stops the investigation safely
with a partial report naming the exact limit.

**Enforcement.** `BudgetLimits` (Pydantic) validates every value against hard
floors/ceilings at construction — including API-supplied overrides — so an
unbounded configuration is unrepresentable. `BudgetService` maintains a
per-case ledger, audits every consumption, and raises `BudgetExceeded`.

**Proof:** `tests/unit/test_budget.py`,
`tests/integration/test_budget_exhaustion.py`,
`tests/adversarial/test_malformed_inputs.py` (1000-fold replay stopped by
budget; endless-retry prevention).

## 6. Case isolation (FR-003, FR-005)

**Guarantee.** Evidence, claims, context, and feedback from one case never
appear in another unless an analyst with access to *both* cases explicitly
links them. No durable cross-case agent memory exists.

**Enforcement.** All case-scoped persistence flows through
`CaseScopedRepository`, which requires an explicit `CaseContext` and
auto-filters every query by `case_id`. Cross-case writes raise
`CaseIsolationError`; cross-case reads return nothing. There is no memory
table, no shared retrieval index, and the model gateway is stateless.

**Proof:** `tests/unit/test_repositories.py`,
`tests/adversarial/test_case_isolation.py` (cross-case claim access,
cross-analyst access on every endpoint, audit-stream scoping),
`tests/adversarial/test_malformed_inputs.py::test_memory_poisoning_no_durable_instruction_store`.

## 7. Tamper-evident audit (FR-028–FR-030)

**Guarantee.** A complete, ordered audit record covers the entire lifecycle;
it is viewable by authorized reviewers and cannot be modified by the agent.

**Enforcement.** See [audit.md](audit.md): append-only service (public API is
exactly `append` / `list_events` / `verify_chain`), per-case SHA-256 hash
chain, no HTTP mutation methods, audit-mutation operations on the policy deny
list.

**Proof:** `tests/unit/test_audit_chain.py`,
`tests/adversarial/test_audit_tamper.py` (direct DB edit and deletion both
detected), `tests/integration/test_audit_completeness.py` (full
reconstruction).

## 8. Secret protection (FR-035 / SC-005)

**Guarantee.** No secret from a connected source appears in a report,
model-visible output, log, or audit interface.

**Enforcement.**

- structlog redaction processors (key-pattern and value-pattern based) applied
  to all log and audit payloads.
- The report verifier scans serialized report output for secret-like values
  before delivery.
- Connector credentials (when real connectors arrive) live only in
  environment/secret stores injected into connector adapters — never in
  prompts, evidence, or reports.

**Proof:** `tests/adversarial/test_secret_extraction.py` — a fake secret
planted in the connector fixtures must never surface through any interface.

## 9. Fail-safe behavior (FR-020, FR-033)

**Guarantee.** Connector outages, malformed tool data, oversized evidence,
missing authorization, ambiguous scope, unresolvable conflicts, budget
exhaustion, unauthorized attempts, manipulation attempts, and missing
provenance all terminate safely — and **no failure ever results in expanded
authorization or weaker controls**.

**Enforcement.** Every workflow state declares a failure transition into a
terminal state; the single finalization routine records the exact reason and
emits a partial report. The policy engine holds no failure-dependent state —
a denial after a failure is evaluated identically.

**Proof:** `tests/unit/test_fail_safe.py`,
`tests/adversarial/test_malformed_inputs.py`,
`tests/integration/test_budget_exhaustion.py`.

## Release gates

Per Constitution Principle VI, the adversarial and safety suites are **binary
release gates** — a single failure blocks release; results are never averaged
into a quality score. `tests/test_traceability.py` additionally fails the
build if any functional requirement loses its test mapping.
