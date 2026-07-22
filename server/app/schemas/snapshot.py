from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SnapshotStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SnapshotCreate(BaseModel):
    repository_uuid: str = Field(min_length=36, max_length=36)
    engine: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=4096)
    manifest: dict[str, Any] = Field(default_factory=dict)


class SnapshotComplete(BaseModel):
    size_bytes: int | None = Field(default=None, ge=0)
    manifest: dict[str, Any] = Field(default_factory=dict)


class SnapshotFail(BaseModel):
    failure_message: str = Field(min_length=1, max_length=4096)


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    repository_uuid: str
    engine: str
    source: str
    status: SnapshotStatus
    size_bytes: int | None
    manifest: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime
