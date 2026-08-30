# Phase 0 Research: Read-Only Alert Investigation Harness

**Date**: 2026-08-28 | **Plan**: [plan.md](./plan.md)

All Technical Context unknowns are resolved below. Format per decision: Decision / Rationale / Alternatives considered.

## R1. Orchestration approach

- **Decision**: Hand-rolled deterministic state machine in plain Python (enum states, transition table, per-state config dataclasses). No agent framework (LangGraph, CrewAI, AutoGen).
- **Rationale**: Constitution V requires an explicit, inspectable state machine with per-state schemas, permitted tools, retries, timeouts, and failure transitions, and Constitution VIII requires minimal architecture. Agent frameworks embed implicit control flow, dynamic tool selection, and framework-managed memory that conflict with deny-by-default and auditability requirements; a transition table of ~12 states + 8 terminal states is small enough to own outright.
- **Alternatives considered**: LangGraph (graph is explicit but pulls large dependency surface and framework-managed state); Temporal (excellent determinism/replay but heavy operational footprint for an MVP pilot); CrewAI/AutoGen (multi-agent orientation prohibited by Constitution VIII).

## R2. Language and web framework

- **Decision**: Python 3.12 + FastAPI + Pydantic v2.
- **Rationale**: Pydantic gives typed, validated tool contracts and state I/O schemas (Constitution: "typed tool interfaces", per-state input/output schemas) with JSON-schema export for contract tests. FastAPI is minimal, well-audited, async-capable for connector I/O. Python has the strongest ecosystem for security-data tooling and LLM clients.
- **Alternatives considered**: TypeScript/Node (viable, weaker schema-validation ergonomics); Go (strong for services, weaker LLM/prompt tooling; slower iteration for evaluation corpus work); Rust (safety not needed at this layer; slows MVP).

## R3. Model provider interface

- **Decision**: litellm as a thin gateway behind an internal `ModelGateway` interface; model + configuration version pinned in config and recorded in every audit trace.
- **Rationale**: Constitution VIII requires replaceable model providers via narrow internal interfaces without delaying the vertical slice. litellm provides one call signature across providers; our own interface keeps it swappable and lets tests use a deterministic fake model.
- **Alternatives considered**: Direct provider SDK (locks in one vendor, still needs our interface anyway); LangChain LLM wrappers (excess dependency surface).

## R4. Storage

- **Decision**: SQLite via SQLAlchemy 2.x for dev/evaluation, PostgreSQL-compatible schema for later pilot. Single database with case-scoped repositories; separate append-only `audit_events` table.
- **Rationale**: One evidence store + one audit mechanism (Constitution VIII). SQLite removes infrastructure friction for the evaluation environment; SQLAlchemy keeps a migration path. Case isolation is enforced at the repository layer (mandatory case_id filter), not by trusting callers.
- **Alternatives considered**: PostgreSQL from day one (better concurrency, but adds ops burden to the MVP); separate audit log file (harder to query for reviewer reconstruction; DB table with hash chain is simpler and queryable).

## R5. Audit tamper evidence

- **Decision**: Append-only audit table where each event stores `prev_hash` and `event_hash` (SHA-256 over canonical JSON + previous hash), forming a per-case hash chain. No UPDATE/DELETE grants for the application role on this table; audit writes go through a single AuditService.
- **Rationale**: Constitution VII: agent must not be able to disable, delete, or rewrite the trail; a hash chain makes any mutation detectable by a reviewer verification pass; simple to implement with zero new dependencies.
- **Alternatives considered**: WORM object storage (production-grade but out of scope for dev/eval environments); external log pipeline (Kafka etc. — excessive for MVP); signed events with KMS (deferred to production pilot feature).

## R6. Untrusted-content handling / prompt-injection resistance

- **Decision**: Layered defenses, none relying on the model as enforcement: (1) all retrieved evidence enters model context inside structural delimiters with an explicit data-not-instructions framing; (2) evidence is never concatenated into system prompts; (3) a deterministic instruction-pattern detector (regex/heuristic ruleset for imperative-to-agent patterns, e.g., "ignore previous instructions", exfiltration requests, tool invocations) flags evidence and emits a `manipulation_detected` audit event (FR-027); (4) the model has no tools — tool selection happens in orchestrator states from the static registry, so injected "tool calls" are inert; (5) output verifier checks the report for policy violations and secrets before delivery.
- **Rationale**: Spec FR-025–FR-027 and constitutional adversarial tests require that injected instructions cannot change objective, permissions, tools, or audit. Making the model incapable of invoking tools directly (orchestrator-mediated tool use only) structurally eliminates the largest injection consequence class.
- **Alternatives considered**: LLM-based injection classifiers (probabilistic; may supplement later but cannot be the enforcement point per Constitution III); content sanitization/stripping (risks destroying evidence integrity — evidence must be preserved verbatim with provenance).

## R7. Analyst authentication (dev/eval scope)

- **Decision**: Bearer tokens (signed JWT) issued by a stub identity provider in dev/eval, with a verification interface designed to swap in the organization's OIDC identity system for the pilot. Token carries analyst ID and data-source authorization claims.
- **Rationale**: Spec assumes analysts authenticate through the organization's existing identity system; that system isn't available in dev/eval. A narrow `IdentityProvider` interface honors the assumption without blocking the vertical slice.
- **Alternatives considered**: Full OIDC integration now (blocks on unavailable org infra); no auth in dev (violates deny-by-default and would leave authorization paths untested).

## R8. Approved data sources for MVP (≤ 3)

- **Decision**: Three synthetic read-only connectors: (1) **Alert source** (SIEM-like alert detail + related events), (2) **Endpoint telemetry** (EDR-like process/file/network events), (3) **Identity/asset context** (directory-like user and asset criticality lookup). All backed by synthetic/sanitized fixture data.
- **Rationale**: Constitution's minimum vertical slice caps sources at three; these three cover the spec's entity types (users, endpoints, processes, files, IPs, applications) and asset-criticality assumption. Synthetic data is explicitly permitted by spec assumptions.
- **Alternatives considered**: Real SIEM/EDR integrations (out of scope for dev/eval; a later shadow-mode feature); more source types (violates the vertical-slice cap).

## R9. Default operational limits (safe system defaults, per clarification)

- **Decision**: Defaults — max elapsed time: 10 min; max tool operations: 50; max retrieved evidence: 500 items / 5 MB total; max model usage: 20 model calls or configured cost ceiling; max retries per failed operation: 2. Organization-overridable per deployment via config; hard floor/ceiling validation prevents unbounded or disabled limits.
- **Rationale**: Clarification session answer requires always-on safe defaults that cannot be disabled. Values sized for pilot alert types; every limit is enforced in deterministic orchestrator code with a budget ledger audited per FR-028.
- **Alternatives considered**: Per-analyst limits (rejected in clarification); mandatory pre-configuration (rejected — investigations must be safe out of the box).

## R10. Report and audit delivery format

- **Decision**: Reports stored as structured JSON (schema-validated, all FR-013 sections) and rendered to Markdown on request; audit reviewer access via JSON API endpoints with chain-verification. No UI in this feature.
- **Rationale**: Spec is UI-agnostic; JSON enables contract tests and downstream integrations, Markdown enables human review; keeps scope minimal per Constitution VIII.
- **Alternatives considered**: Web UI (deferrable, separate feature); PDF export (unnecessary for pilot).

## R11. Testing and adversarial evaluation approach

- **Decision**: pytest with layered suites — contract (schemas/API), unit (policy, budgets, state machine), integration (end-to-end synthetic investigations), adversarial (a versioned hostile-content corpus in `tests/fixtures/` covering every Constitution VI adversarial category). Deterministic fake model for unit/contract tests; recorded/scripted model responses for integration; adversarial suite runs against both fake and real model in the evaluation environment. Safety suites are pass/fail release gates, never averaged.
- **Rationale**: Constitution VI mandates the categories and gate semantics; a versioned corpus makes regression triggers (model/prompt/policy changes) reproducible.
- **Alternatives considered**: External eval platforms (promptfoo, etc. — may complement later; not required for gate coverage); manual red-teaming only (not reproducible or regression-capable).

## R12. Case isolation mechanism

- **Decision**: Repository-layer enforcement: all persistence APIs require an explicit `CaseContext`; queries are automatically filtered by case_id; cross-case reads are impossible through the data-access API; explicit `case_link` records (analyst-created) are the only sanctioned association. No shared retrieval index or durable cross-case memory.
- **Rationale**: FR-003/FR-005 and constitutional isolation tests; structural enforcement beats convention.
- **Alternatives considered**: Row-level security in PostgreSQL (good for pilot, unavailable in SQLite dev path; the repository layer works in both); per-case databases (operationally clumsy).
