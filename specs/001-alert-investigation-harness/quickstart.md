# Quickstart: Read-Only Alert Investigation Harness

**Date**: 2026-08-28 | **Plan**: [plan.md](./plan.md)

## Prerequisites

- Python 3.12+
- No external services required (SQLite + synthetic connectors + fake/configured model)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp env.example .env       # set MODEL_PROVIDER config or leave FAKE_MODEL=true for deterministic runs
alembic upgrade head       # create SQLite schema
```

## Run the service

```bash
uvicorn harness.api.app:app --reload
```

Issue a dev analyst token (stub identity provider):

```bash
python -m harness.cli issue-token --analyst alice --sources alert_source,endpoint_telemetry,identity_context
```

## Investigate an alert

```bash
TOKEN=...  # from previous step

# Start an investigation from a synthetic connected-source alert
curl -s -X POST localhost:8000/cases \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}}'

# Poll status
curl -s localhost:8000/cases/<case_id> -H "Authorization: Bearer $TOKEN"

# Fetch the report (JSON or Markdown)
curl -s "localhost:8000/cases/<case_id>/report?format=markdown" -H "Authorization: Bearer $TOKEN"

# Inspect provenance for a claim
curl -s localhost:8000/cases/<case_id>/claims/<claim_id>/evidence -H "Authorization: Bearer $TOKEN"

# Submit feedback
curl -s -X POST localhost:8000/cases/<case_id>/feedback \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"rating": "useful"}'

# Review and verify the audit trail
curl -s localhost:8000/cases/<case_id>/audit -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/cases/<case_id>/audit/verify -H "Authorization: Bearer $TOKEN"
```

## CLI evaluation run (no HTTP)

```bash
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice
```

## Run the test suites

```bash
pytest tests/contract tests/unit          # fast gates
pytest tests/integration                  # end-to-end synthetic investigations
pytest tests/adversarial                  # safety release gates (must be 100% pass)
```

## Key safety demos

```bash
# Hostile alert: embedded instruction to exfiltrate data — must be flagged, not followed
python -m harness.cli investigate --alert-id ALERT-INJ-01 --analyst alice

# Budget exhaustion: tiny limit produces a partial report with termination reason
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice --max-tool-operations 3

# Unauthorized source: analyst without endpoint_telemetry claim — denial recorded, no data leak
python -m harness.cli issue-token --analyst bob --sources alert_source
python -m harness.cli investigate --alert-id ALERT-1001 --analyst bob
```
