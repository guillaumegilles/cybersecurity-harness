"""Synthetic read-only alert source connector (SIEM-like)."""

from __future__ import annotations

from harness.connectors import fixtures


class ConnectorError(Exception):
    pass


class SourceUnavailable(ConnectorError):
    pass


SOURCE_NAME = "alert_source"

# Toggleable for unavailable-dependency tests.
AVAILABLE = True


def get_alert(alert_id: str) -> dict:
    if not AVAILABLE:
        raise SourceUnavailable(SOURCE_NAME)
    alert = fixtures.ALERTS.get(alert_id)
    if alert is None:
        raise ConnectorError(f"alert not found: {alert_id}")
    return dict(alert)


def get_related_events(alert_id: str, start: str | None = None, end: str | None = None,
                       max_results: int = 200) -> dict:
    if not AVAILABLE:
        raise SourceUnavailable(SOURCE_NAME)
    events = fixtures.RELATED_EVENTS.get(alert_id, [])
    truncated = len(events) > max_results
    return {"events": events[:max_results], "truncated": truncated}
