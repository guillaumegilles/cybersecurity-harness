"""Structured logging with secret redaction and correlation IDs (Constitution VII)."""

from __future__ import annotations

import re
from typing import Any

import structlog

# Patterns that indicate secret material; values matching these are redacted.
SECRET_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|api_?key|private_?key|credential|authorization)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERN = re.compile(
    r"(eyJ[A-Za-z0-9_\-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{20,}|xox[bpars]-[A-Za-z0-9\-]{10,})"
)

REDACTED = "[REDACTED]"


def redact_value(value: Any) -> Any:
    if isinstance(value, str) and SECRET_VALUE_PATTERN.search(value):
        return REDACTED
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value


def redact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in mapping.items():
        if SECRET_KEY_PATTERN.search(str(k)):
            out[k] = REDACTED
        else:
            out[k] = redact_value(v)
    return out


def _redaction_processor(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return redact_mapping(event_dict)


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # correlation-ID propagation
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redaction_processor,
            structlog.processors.JSONRenderer(),
        ]
    )


def bind_correlation(execution_id: str, case_id: str | None = None) -> None:
    structlog.contextvars.bind_contextvars(execution_id=execution_id, case_id=case_id)
