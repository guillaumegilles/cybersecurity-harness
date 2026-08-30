"""Settings and budget-limit configuration.

Safe system defaults ALWAYS apply (FR-031, research R9). Organization may
override per deployment, but hard floors/ceilings prevent unbounded or
disabled limits.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

# Hard bounds — limits can never be disabled or set outside these (FR-031).
_BOUNDS: dict[str, tuple[int, int]] = {
    "max_elapsed_seconds": (10, 3600),
    "max_tool_operations": (1, 500),
    "max_evidence_items": (1, 5000),
    "max_evidence_bytes": (1024, 50_000_000),
    "max_model_calls": (1, 200),
    "max_retries_per_operation": (0, 5),
}


class BudgetLimits(BaseModel):
    """Per-investigation operational limits (FR-031)."""

    max_elapsed_seconds: int = 600
    max_tool_operations: int = 50
    max_evidence_items: int = 500
    max_evidence_bytes: int = 5_000_000
    max_model_calls: int = 20
    max_retries_per_operation: int = 2

    @field_validator("*")
    @classmethod
    def _within_bounds(cls, v: int, info) -> int:  # type: ignore[no-untyped-def]
        lo, hi = _BOUNDS[info.field_name]
        if not (lo <= v <= hi):
            raise ValueError(
                f"{info.field_name}={v} outside permitted bounds [{lo}, {hi}]; "
                "limits cannot be disabled or unbounded (FR-031)"
            )
        return v


class Settings(BaseModel):
    """Application settings."""

    database_url: str = Field(default="sqlite:///harness.db")
    jwt_secret: str = Field(default="dev-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    fake_model: bool = True
    model_name: str = "fake-deterministic-v1"
    policy_version: str = "1.0.0"
    app_version: str = "0.1.0"
    spec_version: str = "001-alert-investigation-harness"
    default_limits: BudgetLimits = Field(default_factory=BudgetLimits)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("DATABASE_URL", "sqlite:///harness.db"),
            jwt_secret=os.environ.get("JWT_SECRET", "dev-only-secret-change-me"),
            fake_model=os.environ.get("FAKE_MODEL", "true").lower() != "false",
            model_name=os.environ.get("MODEL_NAME", "fake-deterministic-v1"),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
