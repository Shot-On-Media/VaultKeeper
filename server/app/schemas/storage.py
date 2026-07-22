from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StorageDriver(StrEnum):
    LOCAL_FILESYSTEM = "local_filesystem"


class StorageStatus(StrEnum):
    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"


class LocalFilesystemConfig(BaseModel):
    path: str = Field(min_length=1, max_length=4096)

    @field_validator("path")
    @classmethod
    def validate_absolute_path(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("path must be absolute")
        return value


class StorageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    driver: Literal[StorageDriver.LOCAL_FILESYSTEM]
    config: LocalFilesystemConfig


class StorageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    config: LocalFilesystemConfig | None = None


class StorageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    driver: StorageDriver
    config: dict[str, Any]
    status: StorageStatus
    last_validated_at: datetime | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime


class StorageValidationResponse(BaseModel):
    uuid: str
    status: StorageStatus
    message: str
    validated_at: datetime
