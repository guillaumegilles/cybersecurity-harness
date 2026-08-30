# Cybersecurity Harness

![License](https://img.shields.io/github/license/guillaumegilles/cybersecurity-harness)
![Stars](https://img.shields.io/github/stars/guillaumegilles/cybersecurity-harness?style=social)
![Issues](https://img.shields.io/github/issues/guillaumegilles/cybersecurity-harness)

> A read-only, evidence-driven AI agent harness that assists SOC analysts with
> investigating a single security alert — with provable safety boundaries,
> full evidence provenance, and a tamper-evident audit trail.

---

## ✨ Features

- **Single-alert investigation** — an authenticated analyst submits or selects one alert and receives a structured, evidence-backed report (timeline, affected entities, hypotheses, confidence levels, recommended next queries)
- **Strictly read-only** — response actions (isolate endpoint, block IP, disable account, run commands…) are architecturally impossible; the agent can only *propose* actions with impact, risk, and rollback details
- **Evidence provenance** — every material claim links to evidence with source, event ID, timestamps, and trust classification; inferences are never presented as observed facts, and missing evidence is stated rather than fabricated
- **Zero-trust tool use** — every tool call is authorized deny-by-default outside the model, against agent identity, analyst claims, case scope, operation, target, and budget
- **Prompt-injection resistance** — all retrieved content is treated as hostile data; the model has no tool access, and manipulation attempts are detected and audited
- **Tamper-evident auditability** — an append-only, SHA-256 hash-chained audit trail lets a reviewer reconstruct every investigation; the agent has no mutation path
- **Safe operational limits** — never-disableable budgets for time, tool calls, evidence volume, model usage, and retries; exhaustion yields a useful partial report with the exact termination reason
- **Case isolation** — cross-case reads are structurally impossible; no durable cross-case agent memory

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- No external services required — synthetic read-only connectors and a deterministic fake model are built in

### Installation

```bash
git clone https://github.com/guillaumegilles/cybersecurity-harness.git
cd cybersecurity-harness
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Running locally

```bash
# CLI investigation (no server needed)
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice

# Or run the HTTP API
uvicorn 'harness.api.app:get_app' --factory
python -m harness.cli issue-token --analyst alice \
  --sources alert_source,endpoint_telemetry,identity_context
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) for the API reference,
or follow the full walkthrough in
[`specs/001-alert-investigation-harness/quickstart.md`](specs/001-alert-investigation-harness/quickstart.md).

### Safety demos

```bash
# Prompt injection: hostile alert content is flagged, never followed
python -m harness.cli investigate --alert-id ALERT-INJ-01 --analyst alice

# Budget exhaustion: safe stop with a partial report and exact reason
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice --max-tool-operations 1
```

### Tests

```bash
pytest tests/contract tests/unit     # fast gates
pytest tests/integration             # end-to-end synthetic investigations
pytest tests/adversarial             # safety release gates (must be 100%)
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2 |
| Orchestration | Hand-rolled deterministic state machine (no agent framework) |
| Model gateway | Deterministic fake model (dev/eval) / litellm (pluggable) |
| Storage | SQLAlchemy 2.x — SQLite (dev/eval), PostgreSQL-compatible |
| Logging | structlog with secret redaction |
| Testing | pytest (contract / unit / integration / adversarial suites) |
| Deployment | Docker + docker-compose (dev & isolated evaluation) |

---

## 📐 Spec-driven development

This project is built with [GitHub Spec Kit](https://github.com/github/spec-kit):

- **Constitution**: [`.specify/memory/constitution.md`](.specify/memory/constitution.md) — non-negotiable safety principles (read-only MVP, zero-trust execution, evidence-driven decisions, deterministic orchestration, mandatory security testing, complete observability)
- **Active feature**: [`specs/001-alert-investigation-harness/`](specs/001-alert-investigation-harness/) — spec, plan, research, data model, contracts, tasks
- **Architecture & safety model**: [`docs/harness.md`](docs/harness.md)

---

## 🗺 Roadmap

- [x] 001 — Read-only alert investigation harness (MVP)
- [ ] PostgreSQL pilot with alembic migrations
- [ ] Read-only shadow-mode pilot against real (sanitized) sources
- [ ] Background/async investigation execution
- [ ] Analyst-facing UI

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) to get
started, and note that every change must comply with the project
[constitution](.specify/memory/constitution.md) — safety requirements are
release gates, not suggestions.

---

## 📄 License

Distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for more information.
