from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationDeliveryResponse,
    NotificationTestCreate,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> NotificationService:
    return NotificationService(session)


@router.get("/channels", response_model=list[NotificationChannelResponse])
def list_channels(
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[NotificationChannelResponse]:
    return service.list_channels()


@router.post(
    "/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    payload: NotificationChannelCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelResponse:
    return service.create_channel(payload)


@router.put("/channels/{channel_uuid}", response_model=NotificationChannelResponse)
def update_channel(
    channel_uuid: str,
    payload: NotificationChannelUpdate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationChannelResponse:
    return service.update_channel(channel_uuid, payload)


@router.delete("/channels/{channel_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_uuid: str,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> Response:
    service.delete_channel(channel_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/channels/{channel_uuid}/test",
    response_model=NotificationDeliveryResponse,
)
def test_channel(
    channel_uuid: str,
    payload: NotificationTestCreate,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationDeliveryResponse:
    return service.test_channel(channel_uuid, payload)


@router.get("/deliveries", response_model=list[NotificationDeliveryResponse])
def list_deliveries(
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[NotificationDeliveryResponse]:
    return service.list_deliveries()
