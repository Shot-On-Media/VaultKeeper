from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BackupEngine(StrEnum):
    FILESYSTEM = "filesystem"
    MARIADB = "mariadb"


class BackupJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class BackupPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    repository_uuid: str = Field(min_length=36, max_length=36)
    engine: BackupEngine
    source: str = Field(min_length=1, max_length=4096)
    interval_minutes: int = Field(ge=1, le=525600)
    enabled: bool = True
    next_run_at: datetime
    max_retries: int = Field(default=3, ge=0, le=10)


class BackupPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    source: str | None = Field(default=None, min_length=1, max_length=4096)
    interval_minutes: int | None = Field(default=None, ge=1, le=525600)
    enabled: bool | None = None
    next_run_at: datetime | None = None
    max_retries: int | None = Field(default=None, ge=0, le=10)


class BackupPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    repository_uuid: str
    name: str
    engine: BackupEngine
    source: str
    interval_minutes: int
    enabled: bool
    next_run_at: datetime
    max_retries: int
    created_at: datetime
    updated_at: datetime


class BackupJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    policy_uuid: str
    status: BackupJobStatus
    attempts: int
    max_attempts: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    snapshot_uuid: str | None
    created_at: datetime
    updated_at: datetime


class SchedulerRunResponse(BaseModel):
    enqueued_jobs: list[BackupJobResponse]


class WorkerRunResponse(BaseModel):
    job: BackupJobResponse | None
