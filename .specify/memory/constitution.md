# Agentic Cybersecurity Harness Constitution

## Core Principles

### I. Specification Before Implementation

Every feature, agent, tool, connector, policy, data source, and user-visible
behavior **MUST** be defined in an approved feature specification before
implementation begins.

Each specification **MUST** define:

- the cybersecurity problem being addressed;
- the intended user and operational outcome;
- the data required;
- the permitted agent capabilities;
- the permitted tools and operations;
- the prohibited behaviors;
- the relevant trust boundaries;
- functional acceptance criteria;
- security acceptance criteria;
- failure and degraded behavior;
- measurable success conditions.

Specifications **MUST** describe required outcomes before prescribing
implementation details.

Every mandatory requirement **MUST** use normative language such as MUST,
MUST NOT, SHOULD, or MAY.

Every MUST and MUST NOT requirement **MUST** be traceable to:

- one or more implementation tasks;
- one or more automated or documented acceptance tests;
- relevant operational telemetry, where applicable.

Implementation **MUST NOT** introduce material behavior that is absent from or
contradicts the approved specification.

If implementation reveals an incomplete, ambiguous, or contradictory requirement,
implementation MUST stop until the specification is clarified and updated.

**Rationale**: The specification is the source of truth. Source code demonstrates
what the system currently does, but the approved specification defines what the
system is permitted and required to do.

### II. Defensive and Read-Only MVP

The MVP **MUST** implement one narrow defensive use case:

> Assist a security analyst in investigating a security alert by collecting
> authorized evidence, constructing a timeline, forming evidence-backed
> hypotheses, identifying missing information, and producing a draft
> investigation report.

The MVP **MAY**:

- retrieve authorized security telemetry;
- normalize security observations;
- correlate events and entities;
- construct an incident timeline;
- calculate deterministic indicators from retrieved evidence;
- formulate investigation hypotheses;
- map observed behavior to an approved security taxonomy;
- recommend additional evidence collection;
- recommend response actions;
- generate a draft investigation report.

The MVP **MUST NOT** autonomously:

- isolate an endpoint;
- disable or suspend an account;
- revoke credentials or sessions;
- delete or quarantine messages;
- modify a firewall or network control;
- change detection rules;
- modify cloud resources;
- exploit a vulnerability;
- establish persistence;
- execute arbitrary commands on a production asset;
- delete or permanently modify business data;
- communicate with an arbitrary external destination.

Recommendations and proposed response actions **MUST** remain distinguishable
from executed actions.

Adding a new use case **MUST** require a separate feature specification.
Apparent model capability is not sufficient justification for expanding the
product scope.

**Rationale**: The MVP exists to validate safe and useful investigation
assistance. It does not exist to demonstrate maximum autonomy.

### III. Zero-Trust Agent Execution

All agent identities, permissions, tools, inputs, outputs, and network
interactions **MUST** be treated according to zero-trust principles.

Every agent execution **MUST** have:

- a unique execution identifier;
- an attributable workload identity;
- an initiating user or system identity;
- a case or investigation identifier;
- an explicit authorization context;
- a defined set of permitted tools;
- a time limit;
- a tool-call limit;
- a cost or model-usage limit;
- a defined termination condition.

Access to tools, resources, networks, and data **MUST** be denied by default.

The absence, ambiguity, or unavailability of an authorization decision **MUST**
result in denial.

Agent permissions **MUST** be:

- limited to the current task;
- restricted to the relevant tenant and case;
- restricted to approved resources;
- restricted to approved operations;
- issued for the shortest practical duration.

Agents **MUST NOT** receive or reuse the interactive credentials of a human user.

Credentials **MUST NOT** appear in:

- prompts;
- source code;
- committed configuration;
- agent memory;
- logs;
- model-visible tool results;
- generated reports.

The language model **MUST NOT** serve as the policy enforcement point.
Authorization, credential issuance, tool validation, network control, and
approval enforcement **MUST** occur outside the model.

An authorization denial **MUST** be treated as an authoritative result. The
agent **MUST NOT** probe alternative operations to discover additional privileges.

**Rationale**: A model instruction is behavioral guidance, not a security boundary.

### IV. Evidence-Driven Decisions

Every material conclusion **MUST** be supported by identifiable evidence.

The system **MUST** distinguish between:

- raw source evidence;
- normalized observation;
- deterministic correlation;
- model-generated hypothesis;
- conclusion;
- recommendation;
- approved action;
- executed action.

Each material observation **MUST** retain available provenance, including:

- source system;
- source record identifier;
- collection timestamp;
- case identifier;
- transformation history;
- trust classification.

The agent **MUST NOT** fabricate:

- events;
- indicators;
- identities;
- assets;
- vulnerabilities;
- tool responses;
- source references;
- investigation results.

If required information is unavailable, the agent **MUST** explicitly state
that it is unavailable.

Each material conclusion **MUST** include:

- supporting evidence;
- known contradicting evidence;
- unresolved questions;
- missing evidence;
- a qualitative or evaluated confidence level.

Confidence scores **MUST NOT** be described as calibrated probabilities unless
calibration has been tested and documented.

The final investigation report **MUST** enable a human analyst to distinguish
observed facts from agent interpretation.

**Rationale**: The principal deliverable is not an answer. It is a reviewable
evidence trail leading to a bounded conclusion.

### V. Deterministic Orchestration

The MVP workflow **MUST** use an explicit and inspectable state machine,
directed graph, or equivalent bounded orchestration mechanism.

The initial workflow **MUST** contain explicit states equivalent to:

```
RECEIVE_ALERT
    -> VALIDATE_REQUEST
    -> AUTHORIZE
    -> CLASSIFY_ALERT
    -> CREATE_INVESTIGATION_PLAN
    -> COLLECT_EVIDENCE
    -> NORMALIZE_EVIDENCE
    -> FORM_HYPOTHESES
    -> VALIDATE_HYPOTHESES
    -> PRODUCE_REPORT
    -> VERIFY_OUTPUT
    -> COMPLETE
```

The workflow **MUST** also define terminal states equivalent to:

```
ACCESS_DENIED
INCOMPLETE_EVIDENCE
SOURCE_UNAVAILABLE
POLICY_BLOCKED
BUDGET_EXCEEDED
VALIDATION_FAILED
CANCELLED
SYSTEM_ERROR
```

Every state **MUST** define:

- accepted input schema;
- produced output schema;
- permitted tools;
- entry conditions;
- exit conditions;
- maximum retries;
- timeout behavior;
- failure transition.

The agent **MUST NOT** create unregistered sub-agents, tools, workflows, or
execution paths at runtime.

Retries **MUST** be bounded.

An operation with side effects **MUST NOT** be retried automatically unless it
has a verified idempotency mechanism.

Models **MAY** assist with classification, summarization, hypothesis generation,
and report drafting. Deterministic code **SHOULD** be used for:

- schema validation;
- authorization;
- policy enforcement;
- timestamp ordering;
- exact matching;
- identifier normalization;
- deduplication;
- limit enforcement;
- audit generation;
- deterministic calculations.

**Rationale**: Probabilistic reasoning may occur inside a deterministic
operational envelope.

### VI. Security Testing Is Mandatory

Security tests **MUST** be written from the approved specification and **MUST**
exist before the corresponding feature is considered complete.

Every feature **MUST** include:

- positive acceptance tests;
- negative acceptance tests;
- authorization-denial tests;
- malformed-input tests;
- unavailable-dependency tests;
- tenant and case isolation tests;
- audit-completeness tests;
- adversarial agent tests.

Relevant adversarial tests **MUST** cover:

- direct prompt injection;
- indirect prompt injection in retrieved evidence;
- malicious instructions in logs or documents;
- attempted privilege escalation;
- tool-argument manipulation;
- malicious or malformed tool responses;
- secret extraction;
- unauthorized network communication;
- memory poisoning;
- cross-case data access;
- cross-tenant data access;
- requests to suppress or alter audit records;
- unsupported conclusions;
- fabricated evidence;
- repeated or replayed operations;
- excessive or endless agent execution.

A feature **MUST NOT** be released when:

- a prohibited operation succeeds;
- an authorization bypass is possible;
- a secret is disclosed to the model or logs;
- tenant or case isolation fails;
- untrusted content changes system policy;
- an audit-critical event is missing;
- a mandatory acceptance criterion fails.

Safety requirements **MUST** act as release gates. They **MUST NOT** be averaged
into a general quality score.

Changes to a model, prompt, policy, workflow, tool, connector, skill, retrieval
source, or execution dependency **MUST** trigger the relevant regression suite.

**Rationale**: Evaluation is part of the product, not a final activity added$
after implementation.

### VII. Complete Observability

Every investigation run **MUST** produce a structured audit trace.

The trace **MUST** record:

- correlation identifier;
- initiating actor;
- agent identity;
- case identifier;
- specification version;
- application version;
- model and model-configuration version;
- policy version;
- workflow transitions;
- tool names and operations;
- securely redacted tool parameters;
- source references;
- authorization decisions;
- limits and budgets;
- errors;
- termination reason;
- final output status.

Audit data **MUST** be protected against modification by the agent.

The agent **MUST NOT** be able to disable, delete, or rewrite its audit trail.

Attempts to conceal activity, suppress logging, or alter the audit trail **MUST**
generate a security event.

Sensitive data **MUST** be redacted, tokenized, or securely referenced.
Observability **MUST NOT** create a secondary secret store.

The system **MUST** retain concise decision summaries and evidence references.
It **MUST NOT** rely on hidden model reasoning as operational evidence.

Logs **MUST** use structured formats and propagate correlation identifiers
across component boundaries.

**Rationale**: An investigation that cannot be reconstructed, reviewed, and
attributed is not acceptable.

### VIII. Simplicity and Minimal Scope

The MVP **MUST** use the smallest architecture capable of satisfying approved
specifications and security controls.

The implementation **SHOULD** initially prefer:

- one supervisor workflow;
- one primary investigation agent;
- read-only connectors;
- typed tool interfaces;
- one policy enforcement layer;
- one evidence store;
- one append-only audit mechanism;
- one evaluation corpus;
- isolated ephemeral execution.

A multi-agent design **MUST NOT** be introduced unless an approved specification
demonstrates that separation provides measurable security, quality, or
operational value.

A new abstraction **MUST** solve an identified requirement or remove demonstrated
repetition. It **MUST NOT** be introduced solely for hypothetical future use.

A new dependency **MUST** have:

- a documented purpose;
- an accountable owner;
- an approved license;
- a pinned or controlled version;
- security and maintenance consideration;
- a removal path.

The MVP **MUST NOT** dynamically install unreviewed skills, plug-ins, connectors,
or dependencies during an investigation.

Model providers and orchestration implementations **SHOULD** remain replaceable
through narrow internal interfaces, but provider abstraction **MUST NOT** delay
the first working vertical slice.

**Rationale**: Complexity enlarges the attack surface and makes agent behavior
harder to test.

## MVP Product Boundaries

### Primary user

The primary MVP user is a cybersecurity analyst investigating a security alert.

### Primary outcome

Given an authorized alert and approved read-only evidence sources, the system
produces:

- a normalized alert summary;
- a timestamped investigation timeline;
- a list of affected entities;
- evidence-backed hypotheses;
- relevant contradicting evidence;
- missing evidence and suggested queries;
- an explicit confidence assessment;
- recommended analyst actions;
- a draft incident report;
- a complete audit trace.

### Minimum vertical slice

The first production-oriented feature **MUST** support:

- input of one security alert;
- retrieval from no more than three approved read-only sources;
- entity and timestamp normalization;
- investigation timeline generation;
- evidence-backed hypothesis generation;
- final structured report generation;
- audit trace generation;
- adversarial evaluation.

### Data boundaries

Only data required for the active investigation **MUST** be provided to the
agent.

Evidence, logs, memory, credentials, and tool results **MUST** be isolated by
tenant and case where applicable.

Every persisted data category **MUST** have:

- a declared purpose;
- an owner;
- an access policy;
- a retention period;
- a deletion procedure.

Durable model memory is **NOT REQUIRED** for the MVP.

If memory is implemented, it **MUST** be scoped, attributable, reviewable, and
deletable. Retrieved content **MUST NOT** directly create durable operational
instructions.

### Tool boundaries

Every tool **MUST** expose a narrow, typed operation with:

- validated input;
- validated output;
- defined authorization scope;
- timeout;
- result-size limit;
- error classification;
- audit event;
- version identifier.

General-purpose shell, unrestricted HTTP, and arbitrary query interfaces are
prohibited in the MVP.

### Deployment boundaries

The MVP **MUST** support a non-production development environment and an
isolated evaluation environment.

Any production-connected pilot **MUST** operate in read-only shadow mode
before broader availability.

## Development and Quality Gates

GitHub Spec Kit structures development around specifications, plans, tasks, and
implementation artifacts. Its constitution is intended to establish principles
and governance that later commands **MUST** follow.

### Gate 1: Constitution

Before running /speckit.specify:

- this constitution **MUST** be ratified;
- constitutional placeholders **MUST** be resolved;
- the MVP boundary **MUST** be accepted;
- unresolved technology selections **MUST** remain planning decisions rather than
speculative constitutional mandates.

### Gate 2: Specification

A feature specification is ready for planning only when it contains:

- validated problem statement;
- prioritized user scenarios;
- explicit scope and exclusions;
- functional requirements;
- security requirements;
- assumptions;
- edge cases;
- measurable success criteria;
- positive acceptance scenarios;
- negative acceptance scenarios;
- adversarial acceptance scenarios;
- no unresolved critical ambiguity.

Specifications **MUST** prioritize what and why. Technology and implementation
choices belong primarily in the plan unless they are permanent constitutional
constraints.

### Gate 3: Plan

The implementation plan **MUST** contain a Constitution Check demonstrating
compliance with every applicable principle.

The plan **MUST** identify:

- trust boundaries;
- component responsibilities;
- agent and user identities;
- data flows;
- tool permissions;
- policy enforcement points;
- isolation mechanism;
- secrets mechanism;
- evidence model;
- audit model;
- failure handling;
- testing strategy;
- deployment and rollback approach.

Any constitutional exception **MUST** be documented in the plan's complexity or
exception tracking section.

### Gate 4: Tasks

Tasks **MUST**** be:

- independently understandable;
- linked to specification requirements;
- ordered by dependency;
- independently testable where possible;
- explicit about files or components affected;
- explicit about security verification.

The task sequence should normally be:

- contracts and schemas;
- acceptance and adversarial test fixtures;
- policies and authorization tests;
- tool adapters;
- workflow states;
- evidence and audit persistence;
- investigation behavior;
- reporting;
- integration testing;
- shadow-deployment controls.

### Gate 5: Implementation

Implementation may begin only after the specification and plan pass their
respective gates.

Every specification implementation **MUST** update the project documentation
under `docs/` so that it accurately reflects the implemented behavior. This
includes, where affected:

- architecture and component responsibilities (`docs/architecture.md`);
- workflow states and transitions (`docs/workflow.md`);
- safety guarantees and their enforcement (`docs/safety-model.md`);
- data model entities and semantics (`docs/data-model.md`);
- API and CLI references (`docs/api.md`, `docs/cli.md`);
- audit event types and reviewer guidance (`docs/audit.md`);
- configuration, limits, and environment variables (`docs/configuration.md`);
- test suites and adversarial coverage (`docs/testing.md`);
- deployment guidance and known limitations (`docs/deployment.md`);
- the documentation index (`docs/README.md`) when documents are added or
  removed.

Documentation updates **MUST** land in the same change set as the
implementation they describe. A feature is not complete while `docs/`
contradicts the implemented behavior.

Implementation **MUST** stop if:

- a requirement is materially ambiguous;
- a security boundary cannot be enforced;
- required test evidence cannot be produced;
- the proposed implementation exceeds the specification;
- a new dependency or architectural component lacks justification.

### Gate 6: Release

A release candidate **MUST** pass:

- unit tests;
- schema and contract tests;
- authorization tests;
- policy tests;
- tenant and case isolation tests;
- workflow-transition tests;
- connector tests;
- audit-completeness tests;
- dependency and secret scans;
- adversarial evaluation;
- approved scenario regression suite.

A release candidate **MUST NOT** ship with documentation in `docs/` that is
missing or inconsistent with the released behavior.

The first operational release **MUST** use shadow mode.

No proposed agent response action may be silently converted into a production action.

## Governance

### Authority

This constitution governs:

- feature specifications;
- clarifications;
- implementation plans;
- task lists;
- architecture decisions;
- source code;
- prompts;
- models;
- agent skills;
- tool definitions;
- policies;
- connectors;
- tests;
- deployment configurations.

When artifacts conflict, the order of precedence is:

1. this constitution;
2. approved security and data policies;
3. approved feature specification;
4. architecture and implementation plan;
5. task list;
6. implementation;
7. informal documentation.

A lower-precedence artifact that conflicts with a higher-precedence artifact is
defective.

### Compliance review

Every pull request **MUST** demonstrate:

- the specification or defect it implements;
- requirements addressed;
- tests added or updated;
- documentation updated under `docs/` (or an explicit statement that no
  document is affected);
- security impact;
- constitutional compliance;
- relevant evaluation results.

Reviewers **MUST** reject changes that introduce unspecified behavior or weaken
a mandatory boundary without an approved constitutional amendment.

### Exceptions

A constitutional exception requires:

- written justification;
- affected principle;
- considered alternatives;
- security consequences;
- accountable owner;
- expiration or review date;
- remediation plan.

Convenience, development speed, and model capability are not sufficient reasons
for bypassing a security principle.

### Amendment procedure

An amendment requires:

- a written proposal;
- the reason for change;
- identification of affected specifications and plans;
- security-impact analysis;
- approval from product, technical, and security owners;
- version update;
- migration or remediation plan when existing implementation is affected.

###Versioning follows semantic principles:

- **MAJOR**: removal or incompatible redefinition of a governing principle;
- **MINOR**: addition of a principle or material expansion of governance;
- **PATCH**: clarification that does not change the intended obligation.

## Emergency changes

Emergency modifications may be used only to contain an active security or
reliability incident.

An emergency change **MUST** have:

- incident identifier;
- accountable incident commander;
- minimal scope;
- rollback method;
- preserved audit trail;
- immediate verification;
- retrospective specification update.

---

**Version**: 1.1.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-08-29
