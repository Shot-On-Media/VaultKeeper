from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.mariadb_backup import (
    MariaDBBackupCreate,
    MariaDBBackupResponse,
    MariaDBDatabaseListResponse,
)
from app.services.mariadb_backup import MariaDBBackupService

router = APIRouter(prefix="/mariadb-backups", tags=["mariadb backups"])


def get_mariadb_backup_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> MariaDBBackupService:
    return MariaDBBackupService(session)


@router.get("/databases", response_model=MariaDBDatabaseListResponse)
def list_databases(
    service: Annotated[MariaDBBackupService, Depends(get_mariadb_backup_service)],
) -> MariaDBDatabaseListResponse:
    return MariaDBDatabaseListResponse(databases=service.discover_databases())


@router.post(
    "",
    response_model=MariaDBBackupResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_mariadb_backup(
    payload: MariaDBBackupCreate,
    service: Annotated[MariaDBBackupService, Depends(get_mariadb_backup_service)],
) -> MariaDBBackupResponse:
    return service.run_backup(payload)
