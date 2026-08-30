"""FastAPI app factory (T019) with auth middleware and error envelope."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from harness.api.identity import AnalystIdentity, IdentityError, get_identity_provider
from harness.config.logging import configure_logging
from harness.storage.db import init_db

_bearer = HTTPBearer(auto_error=False)


def get_analyst(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AnalystIdentity:
    if credentials is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        return get_identity_provider().verify(credentials.credentials)
    except IdentityError:
        raise HTTPException(status_code=401, detail="invalid token")


def create_app(database_url: str | None = None) -> FastAPI:
    configure_logging()
    init_db(database_url)
    app = FastAPI(title="Alert Investigation Harness", version="0.1.0")

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": str(exc.status_code), "message": str(exc.detail)}},
        )

    from harness.api.routes_cases import router as cases_router
    from harness.api.routes_reports import router as reports_router
    from harness.api.routes_evidence import router as evidence_router
    from harness.api.routes_audit import router as audit_router
    from harness.api.routes_feedback import router as feedback_router

    app.include_router(cases_router)
    app.include_router(reports_router)
    app.include_router(evidence_router)
    app.include_router(audit_router)
    app.include_router(feedback_router)
    return app


app = None  # constructed lazily by uvicorn entry: `harness.api.app:get_app()`


def get_app() -> FastAPI:
    global app
    if app is None:
        app = create_app()
    return app
