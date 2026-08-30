# Security Policy

This project is a **security tool**: a read-only, evidence-driven agent harness
for SOC alert investigation. Its safety guarantees (read-only operation,
deny-by-default authorization, tamper-evident audit, prompt-injection
resistance, case isolation) are the product. Weaknesses in those guarantees are
treated as security vulnerabilities, not ordinary bugs.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest (main) | :white_check_mark: |
| < 1.0   | :x:                |

## Scope: what counts as a vulnerability

In addition to classic issues (injection, authn/authz bypass, secret
disclosure), the following harness-specific findings are in scope:

- **Read-only bypass** — any way to make the agent execute a response,
  destructive, administrative, or arbitrary-command operation (FR-017)
- **Authorization bypass** — executing an unregistered tool, reaching an
  unauthorized data source, or turning a policy denial into an allow
- **Prompt injection with effect** — retrieved evidence or analyst-submitted
  content that changes the investigation objective, permissions, tool set,
  policies, or audit records
- **Audit tampering** — any path allowing the agent (or an API caller) to
  suppress, modify, delete, or forge audit events, or defeat hash-chain
  verification
- **Case-isolation breach** — evidence, claims, context, or feedback from one
  case observable from another without an explicit link
- **Secret disclosure** — a secret from a connected source appearing in a
  report, model-visible output, log, or audit interface
- **Budget bypass** — making an investigation run unbounded in time, tool
  calls, evidence volume, model usage, or retries
- **Fail-open behavior** — any failure that results in expanded authorization
  or less restrictive controls (FR-020)

The adversarial test suite (`tests/adversarial/`) encodes these guarantees; a
reproducible violation of any of them is a valid report even if all tests pass.

## Reporting a Vulnerability

> [!WARNING]
> Please do not report security vulnerabilities through public GitHub issues.

Instead, use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/privately-reporting-a-security-vulnerability)
to submit your report. Navigate to the **Security tab** of this repository and
click **Report a vulnerability**.

Please include as much of the following information as possible:

- A description of the vulnerability and its potential impact
- Which safety guarantee is violated (see scope above)
- Steps to reproduce the issue — ideally as a failing adversarial test
- Affected versions
- Any possible mitigations you have identified

You should receive an initial response within 72 hours. We will work with you to
understand and address the issue before any public disclosure.

## Deployment guidance

- The MVP is intended for **non-production development and isolated evaluation
  environments only**; any production-connected pilot must run in read-only
  shadow mode (see the [constitution](.specify/memory/constitution.md))
- The bundled JWT identity provider is a **development stub** — replace
  `JWT_SECRET` and integrate your organization's identity system before any
  shared deployment
- Use only synthetic or sanitized incident data for development and evaluation
