from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import get_database_session
from app.schemas.security import Principal
from app.services.security import SecurityService

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_request_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_security_service(
    session: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> SecurityService:
    return SecurityService(session, settings)


def require_principal(
    request: Request,
    service: Annotated[SecurityService, Depends(get_security_service)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    api_key: Annotated[str | None, Depends(api_key_scheme)],
) -> Principal:
    settings: Settings = request.app.state.settings
    if not settings.security_enabled:
        principal = Principal(actor="development", auth_type="disabled")
        request.state.principal = principal
        return principal

    if bearer is not None:
        principal = service.verify_token(bearer.credentials)
        request.state.principal = principal
        return principal

    if api_key is not None:
        principal = service.principal_from_api_key(api_key)
        if principal is not None:
            request.state.principal = principal
            return principal

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )
