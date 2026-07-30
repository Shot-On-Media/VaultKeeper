from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    enabled: bool = True


class APIKeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    key_prefix: str
    enabled: bool
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class APIKeyCreateResponse(APIKeyResponse):
    secret: str


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    actor: str
    action: str
    path: str
    method: str
    status_code: int
    client_host: str | None
    message: str | None
    created_at: datetime
    updated_at: datetime


class Principal(BaseModel):
    actor: str
    auth_type: str
