from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.snapshot import SnapshotResponse


class MariaDBBackupCreate(BaseModel):
    repository_uuid: str = Field(min_length=36, max_length=36)
    database_name: str | None = Field(default=None, min_length=1, max_length=256)
    managed_server_uuid: str | None = Field(default=None, min_length=36, max_length=36)


class MariaDBDatabaseListResponse(BaseModel):
    databases: list[str]


class MariaDBBackupResponse(BaseModel):
    snapshot: SnapshotResponse
    artifact_path: str
    database_name: str
    dump_bytes: int
    compressed_bytes: int
