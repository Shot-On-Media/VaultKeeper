from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.restore import RestoreCreate, RestoreResponse
from app.services.restore import RestoreService

router = APIRouter(prefix="/restores", tags=["restores"])


def get_restore_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> RestoreService:
    return RestoreService(session)


@router.get("", response_model=list[RestoreResponse])
def list_restores(
    service: Annotated[RestoreService, Depends(get_restore_service)],
) -> list[RestoreResponse]:
    return service.list_restores()


@router.post("", response_model=RestoreResponse, status_code=status.HTTP_201_CREATED)
def restore_snapshot(
    payload: RestoreCreate,
    service: Annotated[RestoreService, Depends(get_restore_service)],
) -> RestoreResponse:
    return service.restore_snapshot(payload)
