from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.schemas.snapshot import SnapshotResponse


class FilesystemBackupCreate(BaseModel):
    repository_uuid: str = Field(min_length=36, max_length=36)
    source_path: str = Field(min_length=1, max_length=4096)
    managed_server_uuid: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("source_path")
    @classmethod
    def validate_absolute_source_path(cls, value: str) -> str:
        if not Path(value).is_absolute():
            raise ValueError("source_path must be absolute")
        return value


class FilesystemBackupResponse(BaseModel):
    snapshot: SnapshotResponse
    artifact_path: str
    file_count: int
    source_bytes: int
    compressed_bytes: int
