---
title: "Alert Investigation Harness"
subtitle: "A read-only, evidence-driven AI agent harness for SOC alert investigation"
---

The **Alert Investigation Harness** assists SOC analysts with investigating a
single security alert — producing a structured, evidence-backed investigation
report while guaranteeing that the agent stays inside explicit authorization,
data-access, time, and tool-use boundaries.

## Key guarantees

| Guarantee | In short |
|---|---|
| **Strictly read-only** | Response actions are architecturally impossible; the agent can only *propose* actions with impact, risk, and rollback |
| **Evidence provenance** | Every material claim links to evidence with source, event ID, timestamps, and trust classification |
| **Zero-trust tool use** | Every tool call authorized deny-by-default, outside the model |
| **Injection resistance** | All retrieved content treated as hostile data; the model has no tool access |
| **Tamper-evident audit** | Append-only, hash-chained trail; reviewers can reconstruct every investigation |
| **Bounded execution** | Never-disableable budgets for time, tools, evidence, model usage, and retries |

## Documentation

| Document | Description |
|----------|-------------|
| [Overview](harness.md) | High-level architecture diagram and safety model summary |
| [Architecture](architecture.md) | Components, trust boundaries, data flows, design decisions |
| [Investigation Workflow](workflow.md) | The deterministic state machine, states, transitions, failure handling |
| [Safety Model](safety-model.md) | Read-only enforcement, zero-trust tool use, injection resistance, budgets |
| [Data Model](data-model.md) | Entities, relationships, provenance and claim typing rules |
| [API Reference](api.md) | HTTP endpoints, authentication, schemas, error semantics |
| [CLI Reference](cli.md) | `issue-token` and `investigate` commands |
| [Audit Trail](audit.md) | Event types, hash chaining, verification, reviewer reconstruction |
| [Configuration](configuration.md) | Environment variables, budget limits and hard bounds |
| [Testing](testing.md) | Test suites, adversarial coverage, traceability, release gates |
| [Deployment](deployment.md) | Local, Docker, environment guidance and production caveats |

## Quick start

```bash
git clone https://github.com/guillaumegilles/cybersecurity-harness.git
cd cybersecurity-harness
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run an investigation from the CLI (no server needed)
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice
```

See the [CLI reference](cli.md) for safety demos (prompt injection, budget
exhaustion, unauthorized sources) and the
[quickstart](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/quickstart.md)
for the full walkthrough.

## Where things are specified

This project is spec-driven ([GitHub Spec Kit](https://github.com/github/spec-kit)).
The authoritative artifacts, in order of precedence:

1. **Constitution** — [`.specify/memory/constitution.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/.specify/memory/constitution.md)
2. **Feature specification** — [`specs/001-alert-investigation-harness/spec.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/spec.md)
3. **Implementation plan** — [`specs/001-alert-investigation-harness/plan.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/plan.md)
4. **Tasks** — [`specs/001-alert-investigation-harness/tasks.md`](https://github.com/guillaumegilles/cybersecurity-harness/blob/main/specs/001-alert-investigation-harness/tasks.md)

Requirement identifiers used throughout these docs (`FR-001`…`FR-035`,
`SC-001`…`SC-010`) refer to the feature specification.
