from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositoryUpdate,
    RepositoryValidationResponse,
)
from app.services.repository import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])


def get_repository_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> RepositoryService:
    return RepositoryService(session)


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> list[RepositoryResponse]:
    return service.list_repositories()


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    payload: RepositoryCreate,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RepositoryResponse:
    return service.create_repository(payload)


@router.put("/{repository_uuid}", response_model=RepositoryResponse)
def update_repository(
    repository_uuid: str,
    payload: RepositoryUpdate,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RepositoryResponse:
    return service.update_repository(repository_uuid, payload)


@router.delete("/{repository_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repository_uuid: str,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> Response:
    service.delete_repository(repository_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{repository_uuid}/validate", response_model=RepositoryValidationResponse)
def validate_repository(
    repository_uuid: str,
    service: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RepositoryValidationResponse:
    return service.validate_repository(repository_uuid)
