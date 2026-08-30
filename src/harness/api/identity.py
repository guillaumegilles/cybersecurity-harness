"""Stub identity provider (research R7).

Issues/verifies signed JWTs carrying analyst ID + data-source authorization
claims. Designed to be swapped for the organization's OIDC system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

import jwt

from harness.config.settings import get_settings


@dataclass(frozen=True)
class AnalystIdentity:
    analyst_id: str
    authorized_sources: tuple[str, ...] = field(default_factory=tuple)


class IdentityError(Exception):
    pass


class IdentityProvider(Protocol):
    def verify(self, token: str) -> AnalystIdentity: ...


class StubIdentityProvider:
    """Dev/eval JWT provider. NOT for production use."""

    def __init__(self, secret: str | None = None) -> None:
        settings = get_settings()
        self._secret = secret or settings.jwt_secret
        self._alg = settings.jwt_algorithm

    def issue(self, analyst_id: str, sources: list[str], ttl_minutes: int = 480) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": analyst_id,
                "sources": sources,
                "iat": now,
                "exp": now + timedelta(minutes=ttl_minutes),
            },
            self._secret,
            algorithm=self._alg,
        )

    def verify(self, token: str) -> AnalystIdentity:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._alg])
        except jwt.PyJWTError as exc:  # absence/ambiguity -> denial (Constitution III)
            raise IdentityError("invalid or expired token") from exc
        sub = payload.get("sub")
        if not sub:
            raise IdentityError("token missing subject")
        return AnalystIdentity(analyst_id=sub, authorized_sources=tuple(payload.get("sources", [])))


_provider: StubIdentityProvider | None = None


def get_identity_provider() -> StubIdentityProvider:
    global _provider
    if _provider is None:
        _provider = StubIdentityProvider()
    return _provider
