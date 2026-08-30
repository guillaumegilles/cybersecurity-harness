# Documentation

Documentation for the **Alert Investigation Harness** — a read-only,
evidence-driven agent harness that assists SOC analysts with investigating a
single security alert.

> **Rendered site**: this documentation is published with
> [Quarto](https://quarto.org) at
> <https://guillaumegilles.github.io/cybersecurity-harness/>.
> The site landing page is [`index.md`](index.md); this README is the GitHub
> entry point.

## Contents

| Document | Description |
|----------|-------------|
| [Overview](harness.md) | High-level architecture diagram and safety model summary |
| [Architecture](architecture.md) | Components, trust boundaries, data flows, design decisions |
| [Investigation Workflow](workflow.md) | The deterministic state machine, states, transitions, failure handling |
| [Safety Model](safety-model.md) | Read-only enforcement, zero-trust tool use, injection resistance, budgets |
| [Data Model](data-model.md) | Entities, relationships, provenance and claim typing rules |
| [API Reference](api.md) | HTTP endpoints, authentication, request/response schemas, error semantics |
| [CLI Reference](cli.md) | `issue-token` and `investigate` commands |
| [Audit Trail](audit.md) | Event types, hash chaining, verification, reviewer reconstruction |
| [Configuration](configuration.md) | Environment variables, budget limits and hard bounds |
| [Testing](testing.md) | Test suites, adversarial coverage, traceability, release gates |
| [Deployment](deployment.md) | Local, Docker, environment guidance and production caveats |

## Where things are specified

This project is spec-driven ([GitHub Spec Kit](https://github.com/github/spec-kit)).
The authoritative artifacts, in order of precedence:

1. **Constitution** — [`.specify/memory/constitution.md`](../.specify/memory/constitution.md)
2. **Feature specification** — [`specs/001-alert-investigation-harness/spec.md`](../specs/001-alert-investigation-harness/spec.md)
3. **Implementation plan** — [`specs/001-alert-investigation-harness/plan.md`](../specs/001-alert-investigation-harness/plan.md)
4. **Tasks** — [`specs/001-alert-investigation-harness/tasks.md`](../specs/001-alert-investigation-harness/tasks.md)

Requirement identifiers used throughout these docs (`FR-001`…`FR-035`,
`SC-001`…`SC-010`) refer to the feature specification.

## Quick start

See [`specs/001-alert-investigation-harness/quickstart.md`](../specs/001-alert-investigation-harness/quickstart.md),
or:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice
```

## Publishing the site locally

```bash
quarto preview          # live preview from the repo root
quarto render           # builds into _site/
```

Publishing to GitHub Pages happens automatically on push to `main` via
[`.github/workflows/publish-docs.yml`](../.github/workflows/publish-docs.yml).
