from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RepositoryStatus(StrEnum):
    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"


class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    storage_uuid: str = Field(min_length=36, max_length=36)


class RepositoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    storage_uuid: str
    name: str
    path: str
    status: RepositoryStatus
    last_validated_at: datetime | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime


class RepositoryValidationResponse(BaseModel):
    uuid: str
    status: RepositoryStatus
    message: str
    validated_at: datetime
