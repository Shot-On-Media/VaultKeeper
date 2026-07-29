from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class VerificationScope(StrEnum):
    REPOSITORY = "repository"
    SNAPSHOT = "snapshot"


class VerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class VerificationReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    repository_uuid: str
    snapshot_uuid: str | None
    scope: VerificationScope
    status: VerificationStatus
    checked_count: int
    failed_count: int
    message: str
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime
