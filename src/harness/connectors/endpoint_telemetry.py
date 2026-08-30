"""Synthetic read-only endpoint telemetry connector (EDR-like)."""

from __future__ import annotations

from harness.connectors import fixtures
from harness.connectors.alert_source import ConnectorError, SourceUnavailable

SOURCE_NAME = "endpoint_telemetry"
AVAILABLE = True


def get_events(endpoint_id: str, start: str | None = None, end: str | None = None,
               event_types: list[str] | None = None, max_results: int = 200) -> dict:
    if not AVAILABLE:
        raise SourceUnavailable(SOURCE_NAME)
    events = fixtures.ENDPOINT_EVENTS.get(endpoint_id)
    if events is None:
        raise ConnectorError(f"endpoint not found: {endpoint_id}")
    if event_types:
        events = [e for e in events if e["event_type"] in event_types]
    truncated = len(events) > max_results
    return {"events": events[:max_results], "truncated": truncated}
