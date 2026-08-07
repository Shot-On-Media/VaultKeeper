from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.filesystem_backup import (
    FilesystemBackupCreate,
    FilesystemBackupResponse,
)
from app.services.filesystem_backup import FilesystemBackupService

router = APIRouter(prefix="/filesystem-backups", tags=["filesystem backups"])


def get_filesystem_backup_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> FilesystemBackupService:
    return FilesystemBackupService(session)


@router.post(
    "",
    response_model=FilesystemBackupResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_filesystem_backup(
    payload: FilesystemBackupCreate,
    service: Annotated[
        FilesystemBackupService,
        Depends(get_filesystem_backup_service),
    ],
) -> FilesystemBackupResponse:
    return service.run_backup(payload)
