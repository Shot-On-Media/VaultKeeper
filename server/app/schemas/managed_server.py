from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManagedServerStatus(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    UNVERIFIED = "unverified"


class ManagedServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hostname: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_username: str = Field(min_length=1, max_length=120)
    ssh_host_key_sha256: str | None = Field(default=None, max_length=128)
    client_path: str = Field(default="vaultkeeper", min_length=1, max_length=4096)
    tags: dict[str, Any] = Field(default_factory=dict)


class ManagedServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    ssh_username: str | None = Field(default=None, min_length=1, max_length=120)
    ssh_host_key_sha256: str | None = Field(default=None, max_length=128)
    client_path: str | None = Field(default=None, min_length=1, max_length=4096)
    tags: dict[str, Any] | None = None


class ManagedServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    hostname: str
    ssh_port: int
    ssh_username: str
    ssh_host_key_sha256: str | None
    client_path: str
    tags: dict[str, Any]
    inventory: dict[str, Any]
    last_inventory_at: datetime | None
    status: ManagedServerStatus
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ManagedServerHostKeyResponse(BaseModel):
    uuid: str
    fingerprint_sha256: str
    trusted: bool
    message: str
    checked_at: datetime


class ManagedServerConnectivityResponse(BaseModel):
    uuid: str
    status: ManagedServerStatus
    host_key_verified: bool
    message: str
    checked_at: datetime


class ManagedServerInventoryResponse(BaseModel):
    uuid: str
    status: ManagedServerStatus
    inventory: dict[str, Any]
    collected_at: datetime
