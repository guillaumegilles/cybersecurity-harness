"""Contract guarantee: prohibited endpoints do not exist (T065, FR-017/FR-030)."""

from __future__ import annotations

PROHIBITED_PATH_FRAGMENTS = [
    "isolate", "block", "quarantine", "execute", "shell", "command",
    "respond", "remediate", "contain",
]


def _paths(client) -> dict:
    return client.app.openapi()["paths"]


def test_no_prohibited_endpoints(client):
    for path in _paths(client):
        for frag in PROHIBITED_PATH_FRAGMENTS:
            assert frag not in path.lower(), f"prohibited endpoint present: {path}"


def test_no_audit_mutation_endpoints(client):
    """No PUT/PATCH/DELETE on audit resources (FR-030)."""
    for path, ops in _paths(client).items():
        if "audit" in path:
            assert set(ops) <= {"get", "head"}, f"audit mutation possible: {path}"


def test_no_runtime_tool_registration_endpoint(client):
    for path, ops in _paths(client).items():
        if "tool" in path.lower():
            assert set(ops) <= {"get", "head"}


def test_no_delete_put_patch_methods_anywhere(client):
    """Strictly read-only + append-only API surface."""
    for path, ops in _paths(client).items():
        assert not ({"delete", "put", "patch"} & set(ops)), f"mutation method on {path}"
