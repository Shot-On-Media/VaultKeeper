from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.storage import (
    StorageCreate,
    StorageResponse,
    StorageUpdate,
    StorageValidationResponse,
)
from app.services.storage import StorageService

router = APIRouter(prefix="/storage", tags=["storage"])


def get_storage_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> StorageService:
    return StorageService(session)


@router.get("", response_model=list[StorageResponse])
def list_storage(
    service: Annotated[StorageService, Depends(get_storage_service)],
) -> list[StorageResponse]:
    return service.list_storage()


@router.post("", response_model=StorageResponse, status_code=status.HTTP_201_CREATED)
def create_storage(
    payload: StorageCreate,
    service: Annotated[StorageService, Depends(get_storage_service)],
) -> StorageResponse:
    return service.create_storage(payload)


@router.put("/{storage_uuid}", response_model=StorageResponse)
def update_storage(
    storage_uuid: str,
    payload: StorageUpdate,
    service: Annotated[StorageService, Depends(get_storage_service)],
) -> StorageResponse:
    return service.update_storage(storage_uuid, payload)


@router.delete("/{storage_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_storage(
    storage_uuid: str,
    service: Annotated[StorageService, Depends(get_storage_service)],
) -> Response:
    service.delete_storage(storage_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{storage_uuid}/validate", response_model=StorageValidationResponse)
def validate_storage(
    storage_uuid: str,
    service: Annotated[StorageService, Depends(get_storage_service)],
) -> StorageValidationResponse:
    return service.validate_storage(storage_uuid)
