from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RestoreStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RestoreCreate(BaseModel):
    snapshot_uuid: str = Field(min_length=36, max_length=36)
    target_path: str = Field(min_length=1, max_length=4096)

    @field_validator("target_path")
    @classmethod
    def validate_absolute_target_path(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("target_path must be absolute")
        return value


class RestoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    snapshot_uuid: str
    status: RestoreStatus
    target_path: str
    progress_percent: int
    verification_message: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
