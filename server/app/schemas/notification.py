from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationDriver(StrEnum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    NTFY = "ntfy"


class NotificationDeliveryStatus(StrEnum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    driver: NotificationDriver
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any], info: Any) -> dict[str, Any]:
        driver = info.data.get("driver")
        if driver is NotificationDriver.NTFY:
            cls._require_string(value, "server_url")
            cls._require_string(value, "topic")
        if driver is NotificationDriver.WEBHOOK:
            cls._require_string(value, "url")
        if driver is NotificationDriver.EMAIL:
            cls._require_string(value, "recipient")
        return value

    @classmethod
    def _require_string(cls, value: dict[str, Any], key: str) -> None:
        if not isinstance(value.get(key), str) or value[key] == "":
            raise ValueError(f"config.{key} is required")


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class NotificationTestCreate(BaseModel):
    title: str = Field(default="VaultKeeper notification test", max_length=180)
    message: str = Field(default="VaultKeeper can deliver notifications.", min_length=1)


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    name: str
    driver: NotificationDriver
    enabled: bool
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NotificationDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    channel_uuid: str
    channel_name: str
    driver: NotificationDriver
    event_type: str
    status: NotificationDeliveryStatus
    title: str
    message: str
    response_code: int | None
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
