"""Shared test fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import harness.api.app as app_module
import harness.storage.db as db_module
from harness.api.identity import get_identity_provider

ALL_SOURCES = ["alert_source", "endpoint_telemetry", "identity_context"]


@pytest.fixture()
def db(tmp_path):
    """Fresh SQLite DB per test."""
    db_module._engine = None
    db_module._session_factory = None
    db_module.init_db(f"sqlite:///{tmp_path}/test.db")
    yield
    db_module._engine = None
    db_module._session_factory = None


@pytest.fixture()
def session(db):
    return db_module.get_session()


@pytest.fixture()
def client(tmp_path):
    db_module._engine = None
    db_module._session_factory = None
    app_module.app = None
    app = app_module.create_app(f"sqlite:///{tmp_path}/api.db")
    with TestClient(app) as c:
        yield c
    app_module.app = None
    db_module._engine = None
    db_module._session_factory = None


def auth(analyst: str = "alice", sources: list[str] | None = None) -> dict[str, str]:
    token = get_identity_provider().issue(analyst, sources if sources is not None else ALL_SOURCES)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def headers():
    return auth()
