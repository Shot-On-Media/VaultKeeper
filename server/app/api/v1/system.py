from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.system import HealthResponse, VersionResponse
from app.services.health import build_health_response, build_version_response

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return build_health_response(get_settings())


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return build_version_response(get_settings())
