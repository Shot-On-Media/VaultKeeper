from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.session import SessionLocal
from app.services.security import SecurityService
from app.workers.scheduler_loop import run_scheduler_loop


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        settings: Settings = request.app.state.settings
        if (
            settings.security_enabled
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path.startswith("/api/v1/")
            and request.url.path != "/api/v1/auth/login"
        ):
            principal = getattr(request.state, "principal", None)
            actor = principal.actor if principal is not None else "anonymous"
            session_factory = getattr(
                request.app.state,
                "audit_session_factory",
                SessionLocal,
            )
            with session_factory() as session:
                SecurityService(session, settings).record_audit(
                    actor=actor,
                    action=f"{request.method} {request.url.path}",
                    path=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    client_host=request.client.host if request.client else None,
                )
        return response


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = application.state.settings
    scheduler_task: asyncio.Task[None] | None = None
    if settings.scheduler_enabled:
        scheduler_task = asyncio.create_task(
            run_scheduler_loop(settings.scheduler_interval_seconds)
        )
    try:
        yield
    finally:
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.app_env)
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.audit_session_factory = SessionLocal
    application.add_middleware(AuditMiddleware)
    application.include_router(api_v1_router)
    return application


app = create_app()
