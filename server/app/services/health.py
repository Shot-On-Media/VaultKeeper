from __future__ import annotations

from datetime import UTC, datetime

import redis
import structlog
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.database.session import engine, redis_client
from app.schemas.system import HealthResponse, VersionResponse

logger = structlog.get_logger(__name__)


def dependency_status(
    database_engine: Engine = engine,
    cache_client: redis.Redis = redis_client,
) -> dict[str, str]:
    status = {"database": "online", "redis": "online"}

    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        status["database"] = "offline"

    try:
        cache_client.ping()
    except redis.RedisError as exc:
        logger.warning("redis_health_check_failed", error=str(exc))
        status["redis"] = "offline"

    return status


def build_health_response(settings: Settings) -> HealthResponse:
    dependencies = dependency_status()
    healthy = all(value == "online" for value in dependencies.values())

    return HealthResponse(
        status="healthy" if healthy else "degraded",
        api="online",
        database=dependencies["database"],
        redis=dependencies["redis"],
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


def build_version_response(settings: Settings) -> VersionResponse:
    return VersionResponse(
        application="VaultKeeper",
        version=settings.app_version,
        codename=settings.app_codename,
        repository_format=1,
        database_schema=1,
        protocol=1,
    )
