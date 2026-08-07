from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.security import get_security_service, require_principal
from app.schemas.security import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
    AuditLogResponse,
    Principal,
)
from app.services.security import SecurityService

router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(require_principal)],
)


@router.get("/api-keys", response_model=list[APIKeyResponse])
def list_api_keys(
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> list[APIKeyResponse]:
    return service.list_api_keys()


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    payload: APIKeyCreate,
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> APIKeyCreateResponse:
    return service.create_api_key(payload)


@router.put("/api-keys/{api_key_uuid}", response_model=APIKeyResponse)
def update_api_key(
    api_key_uuid: str,
    payload: APIKeyUpdate,
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> APIKeyResponse:
    return service.update_api_key(api_key_uuid, payload)


@router.delete("/api-keys/{api_key_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_uuid: str,
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> Response:
    service.delete_api_key(api_key_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> list[AuditLogResponse]:
    return service.list_audit_logs()


@router.get("/me", response_model=Principal)
def current_principal(
    principal: Annotated[Principal, Depends(require_principal)],
) -> Principal:
    return principal
