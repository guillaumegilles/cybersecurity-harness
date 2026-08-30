# Configuration

Implementation: `src/harness/config/settings.py`. Configuration comes from
environment variables (see `env.example`).

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///harness.db` | SQLAlchemy database URL. SQLite for dev/eval; schema is PostgreSQL-compatible |
| `JWT_SECRET` | `dev-only-secret-change-me` | HMAC secret for the stub identity provider. **Must** be replaced in any shared deployment |
| `FAKE_MODEL` | `true` | `true` → deterministic `FakeModel`; `false` → litellm-backed provider (requires `pip install -e ".[llm]"`) |
| `MODEL_NAME` | `fake-deterministic-v1` | Model identifier passed to litellm when `FAKE_MODEL=false`; recorded in every case for reproducibility |

Version metadata (`app_version`, `spec_version`, `policy_version`) is pinned
in code and stamped onto every case and audit context (Constitution VII).

## Budget limits (FR-031)

Safe defaults **always** apply. A deployment may override them — via
`Settings.default_limits`, per-request `limit_overrides`, or CLI flags — but
every value is validated against hard floors/ceilings at construction time,
so a disabled or unbounded limit is unrepresentable.

| Limit | Default | Hard bounds |
|---|---|---|
| `max_elapsed_seconds` | 600 (10 min) | 10 – 3600 |
| `max_tool_operations` | 50 | 1 – 500 |
| `max_evidence_items` | 500 | 1 – 5000 |
| `max_evidence_bytes` | 5 000 000 (5 MB) | 1024 – 50 000 000 |
| `max_model_calls` | 20 | 1 – 200 |
| `max_retries_per_operation` | 2 | 0 – 5 |

Out-of-bounds overrides are rejected: the API returns `400`, the CLI raises a
validation error. The effective limits are snapshotted onto the case
(`InvestigationCase.limits`) so later configuration changes never alter a
recorded investigation's contract.

## Logging

`src/harness/config/logging.py` configures structlog with:

- **JSON rendering** and ISO timestamps
- **Correlation-ID propagation** (`execution_id`, `case_id`) via contextvars
- **Secret redaction** — key patterns (`password`, `secret`, `token`,
  `api_key`, `credential`, `authorization`, …) and value patterns (JWTs,
  private key blocks, AWS access keys, GitHub/Slack token shapes) are replaced
  with `[REDACTED]` before anything is written

The same redaction functions are applied to audit payloads and tool
parameters, so no interface receives unredacted secret material.

## Tool registry configuration

The tool registry is **static code** (`src/harness/tools/registry.py`), not
runtime configuration — deliberately. Adding a tool requires a code change,
review, and a spec update (FR-021 / Constitution: no dynamic tool
installation). Each entry pins: version, single operation, Pydantic I/O
schemas, authorization scope, timeout, and max result size.

## Identity provider

The bundled `StubIdentityProvider` (HS256 JWTs) exists for dev/eval only. It
sits behind the narrow `IdentityProvider` protocol
(`src/harness/api/identity.py`) — integrate the organization's OIDC/identity
system by providing another implementation of `verify(token) →
AnalystIdentity` without touching any caller.

Token claims:

```json
{ "sub": "alice", "sources": ["alert_source", "endpoint_telemetry"], "iat": …, "exp": … }
```

`sources` drives per-source authorization in the policy engine: an analyst
without a source claim receives opaque denials for that source (FR-019).
