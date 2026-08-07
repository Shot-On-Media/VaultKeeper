from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.security import get_security_service
from app.schemas.security import LoginRequest, TokenResponse
from app.services.security import SecurityService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: Annotated[SecurityService, Depends(get_security_service)],
) -> TokenResponse:
    return service.login(payload)
