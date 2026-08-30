"""Synthetic read-only identity/asset context connector (directory-like)."""

from __future__ import annotations

from harness.connectors import fixtures
from harness.connectors.alert_source import ConnectorError, SourceUnavailable

SOURCE_NAME = "identity_context"
AVAILABLE = True


def get_user(user_id: str) -> dict:
    if not AVAILABLE:
        raise SourceUnavailable(SOURCE_NAME)
    user = fixtures.USERS.get(user_id)
    if user is None:
        raise ConnectorError(f"user not found: {user_id}")
    return dict(user)


def get_asset(asset_id: str) -> dict:
    if not AVAILABLE:
        raise SourceUnavailable(SOURCE_NAME)
    asset = fixtures.ASSETS.get(asset_id)
    if asset is None:
        raise ConnectorError(f"asset not found: {asset_id}")
    return dict(asset)
