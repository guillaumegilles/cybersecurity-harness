"""Synthetic corpus re-export for tests (T017). Source of truth lives in the
connector fixtures so connectors and tests share identical data."""

from harness.connectors.fixtures import (  # noqa: F401
    ALERTS,
    ASSETS,
    ENDPOINT_EVENTS,
    PLANTED_SECRET,
    RELATED_EVENTS,
    USERS,
)
