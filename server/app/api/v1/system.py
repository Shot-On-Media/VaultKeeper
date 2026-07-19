from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import redis
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.database.session import engine, redis_client

router = APIRouter(tags=["system"])


def dependency_status() -> dict[str, str]:
    status = {"database": "online", "redis": "online"}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        status["database"] = "offline"

    try:
        redis_client.ping()
    except redis.RedisError:
        status["redis"] = "offline"

    return status


@router.get("/health")
def health() -> dict[str, Any]:
    dependencies = dependency_status()
    healthy = all(value == "online" for value in dependencies.values())
    settings = get_settings()

    return {
        "status": "healthy" if healthy else "degraded",
        "api": "online",
        **dependencies,
        "version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/version")
def version() -> dict[str, Any]:
    settings = get_settings()

    return {
        "application": "VaultKeeper",
        "version": settings.app_version,
        "codename": settings.app_codename,
        "repository_format": 1,
        "database_schema": 1,
        "protocol": 1,
    }
