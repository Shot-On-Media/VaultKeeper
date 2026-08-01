from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.managed_server import (
    ManagedServerCreate,
    ManagedServerResponse,
    ManagedServerUpdate,
)
from app.services.managed_server import ManagedServerService

router = APIRouter(prefix="/managed-servers", tags=["managed-servers"])


def get_managed_server_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> ManagedServerService:
    return ManagedServerService(session)


@router.get("", response_model=list[ManagedServerResponse])
def list_servers(
    service: Annotated[ManagedServerService, Depends(get_managed_server_service)],
) -> list[ManagedServerResponse]:
    return service.list_servers()


@router.post(
    "", response_model=ManagedServerResponse, status_code=status.HTTP_201_CREATED
)
def create_server(
    payload: ManagedServerCreate,
    service: Annotated[ManagedServerService, Depends(get_managed_server_service)],
) -> ManagedServerResponse:
    return service.create_server(payload)


@router.put("/{server_uuid}", response_model=ManagedServerResponse)
def update_server(
    server_uuid: str,
    payload: ManagedServerUpdate,
    service: Annotated[ManagedServerService, Depends(get_managed_server_service)],
) -> ManagedServerResponse:
    return service.update_server(server_uuid, payload)


@router.delete("/{server_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_uuid: str,
    service: Annotated[ManagedServerService, Depends(get_managed_server_service)],
) -> Response:
    service.delete_server(server_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
