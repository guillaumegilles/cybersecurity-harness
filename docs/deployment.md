# Deployment

> **Scope caveat (constitutional):** the MVP targets **non-production
> development and isolated evaluation environments only**. Any
> production-connected pilot must run in read-only shadow mode and requires
> its own feature specification.

## Local (venv)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp env.example .env

# CLI-only usage — no server needed
python -m harness.cli investigate --alert-id ALERT-1001 --analyst alice

# HTTP API
uvicorn 'harness.api.app:get_app' --factory --host 127.0.0.1 --port 8000
```

## Docker

```bash
docker compose up --build
# harness available on http://localhost:8000, data persisted in the harness-data volume
```

The image (`Dockerfile`) runs with `FAKE_MODEL=true` and SQLite at
`/data/harness.db` by default. Override via environment:

```yaml
environment:
  FAKE_MODEL: "false"
  MODEL_NAME: "openai/gpt-4o-mini"     # any litellm-supported identifier
  JWT_SECRET: "<long random secret>"
  DATABASE_URL: "sqlite:////data/harness.db"
```

Using a real model additionally requires the `llm` extra
(`pip install -e ".[llm]"` in a derived image) and the provider's API key in
the environment. **Never** bake keys into images or compose files.

## Environments

| Environment | Model | Data | Identity |
|---|---|---|---|
| Development | `FakeModel` | Synthetic fixtures | Stub JWT (default secret acceptable locally) |
| Evaluation (isolated) | Fake **and** real model (adversarial suite runs against both) | Synthetic/sanitized only | Stub JWT with a strong, per-environment `JWT_SECRET` |
| Pilot (future feature) | Pinned real model | Read-only shadow connections | Organization OIDC via the `IdentityProvider` protocol |

## Pre-deployment checklist

- [ ] `pytest tests -q` — all suites green
- [ ] `pytest tests/adversarial -q` — 100 % (release gate, never waived)
- [ ] `JWT_SECRET` replaced (≥ 32 random bytes)
- [ ] `FAKE_MODEL` / `MODEL_NAME` set intentionally; model version will be
      stamped onto every case
- [ ] Budget defaults reviewed for the deployment
      (`src/harness/config/settings.py`); overrides stay within hard bounds
- [ ] Database volume backed up / lifecycle defined (audit retention)
- [ ] No secrets in images, compose files, or committed configuration

## Rollback

Deployments are stateless containers over a database volume:

- **Application rollback**: redeploy the previous image + configuration. The
  schema is additive in the dev/eval line, so older images tolerate newer
  databases; verify before relying on this across bigger jumps.
- **Model rollback**: change `MODEL_NAME` — every case records the model
  version it ran with, so results remain attributable.
- **Data**: never mutate or trim `audit_events` as part of a rollback; the
  audit trail is append-only by policy as well as by code.

## Known dev/eval limitations

| Limitation | Production path |
|---|---|
| SQLite storage | PostgreSQL pilot (schema is compatible; alembic migrations arrive then) |
| Synchronous investigation execution in the API request | Background workers / task queue |
| Stub JWT identity | Organization OIDC behind `IdentityProvider` |
| Hash chain = tamper *evidence* only | WORM/object-lock audit storage, signed events |
| Synthetic connectors | Approved read-only production connectors in shadow mode |
