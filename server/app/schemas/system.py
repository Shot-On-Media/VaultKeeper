from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DependencyState = Literal["online", "offline", "unknown"]
HealthState = Literal["healthy", "degraded"]


class HealthResponse(BaseModel):
    status: HealthState
    api: Literal["online"]
    database: DependencyState
    redis: DependencyState
    version: str
    timestamp: datetime


class VersionResponse(BaseModel):
    application: Literal["VaultKeeper"]
    version: str
    codename: str
    repository_format: int
    database_schema: int
    protocol: int
