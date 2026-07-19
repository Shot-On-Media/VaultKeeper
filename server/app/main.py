from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import redis
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

APP_VERSION = "0.1.0-alpha1"
CODENAME = "Foundation"


def database_url() -> str:
    user = os.environ["VK_DB_USER"]
    password = os.environ["VK_DB_PASSWORD"]
    host = os.getenv("VK_DB_HOST", "mariadb")
    port = os.getenv("VK_DB_PORT", "3306")
    name = os.environ["VK_DB_NAME"]
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


engine = create_engine(database_url(), pool_pre_ping=True)
redis_client = redis.Redis.from_url(
    os.getenv("VK_REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
)

app = FastAPI(
    title="VaultKeeper API",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


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


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    dependencies = dependency_status()
    healthy = all(value == "online" for value in dependencies.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "api": "online",
        **dependencies,
        "version": APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/v1/version")
def version() -> dict[str, Any]:
    return {
        "application": "VaultKeeper",
        "version": APP_VERSION,
        "codename": CODENAME,
        "repository_format": 1,
        "database_schema": 1,
        "protocol": 1,
    }
