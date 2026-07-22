from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.app_env)
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.include_router(api_v1_router)
    return application


app = create_app()
