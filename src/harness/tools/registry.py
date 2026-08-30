"""Static tool registry (T014, FR-021).

Loaded at import time from code — no runtime registration path exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, Field

from harness.connectors import alert_source, endpoint_telemetry, identity_context


# --- Typed I/O schemas per contracts/tools.md ---


class GetAlertInput(BaseModel):
    alert_id: str


class GetRelatedEventsInput(BaseModel):
    alert_id: str
    start: str | None = None
    end: str | None = None
    max_results: int = Field(default=200, le=200, ge=1)


class GetEndpointEventsInput(BaseModel):
    endpoint_id: str
    start: str | None = None
    end: str | None = None
    event_types: list[str] | None = None
    max_results: int = Field(default=200, le=200, ge=1)


class GetUserInput(BaseModel):
    user_id: str


class GetAssetInput(BaseModel):
    asset_id: str


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    version: str
    operation: str
    source: str
    input_schema: type[BaseModel]
    handler: Callable[..., dict]
    authorization_scope: str
    timeout_seconds: int = 30
    max_result_bytes: int = 1_000_000
    error_classification: tuple[str, ...] = (
        "unavailable",
        "malformed_result",
        "unauthorized",
        "timeout",
        "oversized_result",
    )


TOOL_REGISTRY: dict[str, RegisteredTool] = {
    "alert_source.get_alert": RegisteredTool(
        name="alert_source.get_alert",
        version="1.0.0",
        operation="alert_source.get_alert",
        source="alert_source",
        input_schema=GetAlertInput,
        handler=alert_source.get_alert,
        authorization_scope="alert_source:read",
    ),
    "alert_source.get_related_events": RegisteredTool(
        name="alert_source.get_related_events",
        version="1.0.0",
        operation="alert_source.get_related_events",
        source="alert_source",
        input_schema=GetRelatedEventsInput,
        handler=alert_source.get_related_events,
        authorization_scope="alert_source:read",
    ),
    "endpoint_telemetry.get_events": RegisteredTool(
        name="endpoint_telemetry.get_events",
        version="1.0.0",
        operation="endpoint_telemetry.get_events",
        source="endpoint_telemetry",
        input_schema=GetEndpointEventsInput,
        handler=endpoint_telemetry.get_events,
        authorization_scope="endpoint_telemetry:read",
    ),
    "identity_context.get_user": RegisteredTool(
        name="identity_context.get_user",
        version="1.0.0",
        operation="identity_context.get_user",
        source="identity_context",
        input_schema=GetUserInput,
        handler=identity_context.get_user,
        authorization_scope="identity_context:read",
    ),
    "identity_context.get_asset": RegisteredTool(
        name="identity_context.get_asset",
        version="1.0.0",
        operation="identity_context.get_asset",
        source="identity_context",
        input_schema=GetAssetInput,
        handler=identity_context.get_asset,
        authorization_scope="identity_context:read",
    ),
}

REGISTERED_OPERATIONS: frozenset[str] = frozenset(TOOL_REGISTRY.keys())


def get_tool(name: str) -> RegisteredTool | None:
    return TOOL_REGISTRY.get(name)
