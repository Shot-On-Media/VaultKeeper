from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import NotificationChannel, NotificationDelivery
from app.repositories.notification import (
    NotificationChannelRepository,
    NotificationDeliveryRepository,
)
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationDeliveryResponse,
    NotificationDeliveryStatus,
    NotificationDriver,
    NotificationTestCreate,
)


@dataclass(frozen=True)
class NotificationEvent:
    event_type: str
    title: str
    message: str
    priority: str = "default"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeliveryResult:
    status: NotificationDeliveryStatus
    response_code: int | None = None
    error_message: str | None = None


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.channel_repository = NotificationChannelRepository(session)
        self.delivery_repository = NotificationDeliveryRepository(session)

    def list_channels(self) -> list[NotificationChannelResponse]:
        return [
            self._channel_to_response(channel)
            for channel in self.channel_repository.list()
        ]

    def create_channel(
        self,
        payload: NotificationChannelCreate,
    ) -> NotificationChannelResponse:
        if self.channel_repository.get_by_name(payload.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Notification channel name already exists.",
            )
        channel = NotificationChannel(
            name=payload.name,
            driver=payload.driver.value,
            enabled=payload.enabled,
            config=payload.config,
        )
        self.channel_repository.add(channel)
        self.session.commit()
        self.session.refresh(channel)
        return self._channel_to_response(channel)

    def update_channel(
        self,
        channel_uuid: str,
        payload: NotificationChannelUpdate,
    ) -> NotificationChannelResponse:
        channel = self._get_channel(channel_uuid)
        if payload.name is not None and payload.name != channel.name:
            if self.channel_repository.get_by_name(payload.name) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Notification channel name already exists.",
                )
            channel.name = payload.name
        if payload.enabled is not None:
            channel.enabled = payload.enabled
        if payload.config is not None:
            channel.config = payload.config
        self.session.commit()
        self.session.refresh(channel)
        return self._channel_to_response(channel)

    def delete_channel(self, channel_uuid: str) -> None:
        channel = self._get_channel(channel_uuid)
        self.channel_repository.delete(channel)
        self.session.commit()

    def list_deliveries(self) -> list[NotificationDeliveryResponse]:
        return [
            self._delivery_to_response(delivery)
            for delivery in self.delivery_repository.list()
        ]

    def test_channel(
        self,
        channel_uuid: str,
        payload: NotificationTestCreate,
    ) -> NotificationDeliveryResponse:
        channel = self._get_channel(channel_uuid)
        event = NotificationEvent(
            event_type="notification.test",
            title=payload.title,
            message=payload.message,
            priority="default",
            tags=("white_check_mark",),
        )
        delivery = self._deliver_to_channel(channel, event)
        self.session.commit()
        self.session.refresh(delivery)
        return self._delivery_to_response(delivery)

    def notify_event(
        self, event: NotificationEvent
    ) -> list[NotificationDeliveryResponse]:
        deliveries: list[NotificationDeliveryResponse] = []
        for channel in self.channel_repository.list_enabled():
            delivery = self._deliver_to_channel(channel, event)
            deliveries.append(self._delivery_to_response(delivery))
        self.session.commit()
        return deliveries

    def _deliver_to_channel(
        self,
        channel: NotificationChannel,
        event: NotificationEvent,
    ) -> NotificationDelivery:
        result = self._send(channel, event)
        delivery = NotificationDelivery(
            channel_id=channel.id,
            event_type=event.event_type,
            status=result.status.value,
            title=event.title,
            message=event.message,
            response_code=result.response_code,
            error_message=result.error_message,
            sent_at=(
                datetime.now(UTC)
                if result.status is NotificationDeliveryStatus.SENT
                else None
            ),
        )
        self.delivery_repository.add(delivery)
        return delivery

    def _send(
        self,
        channel: NotificationChannel,
        event: NotificationEvent,
    ) -> DeliveryResult:
        driver = NotificationDriver(channel.driver)
        if driver is NotificationDriver.NTFY:
            return self._send_ntfy(channel.config, event)
        if driver is NotificationDriver.WEBHOOK:
            return self._send_webhook(channel.config, event)
        return DeliveryResult(
            status=NotificationDeliveryStatus.SKIPPED,
            error_message="Email delivery is not configured yet.",
        )

    def _send_ntfy(
        self,
        config: dict[str, Any],
        event: NotificationEvent,
    ) -> DeliveryResult:
        server_url = str(config["server_url"]).rstrip("/") + "/"
        topic = quote(str(config["topic"]).strip("/"))
        url = urljoin(server_url, topic)
        headers = {
            "Title": event.title,
            "Priority": str(config.get("priority", event.priority)),
            "Tags": ",".join(event.tags or tuple(config.get("tags", ()))),
        }
        token = config.get("token")
        if isinstance(token, str) and token:
            headers["Authorization"] = f"Bearer {token}"
        return self._post_text(url, event.message, headers)

    def _send_webhook(
        self,
        config: dict[str, Any],
        event: NotificationEvent,
    ) -> DeliveryResult:
        url = str(config["url"])
        headers = {"Content-Type": "application/json"}
        token = config.get("token")
        if isinstance(token, str) and token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = httpx.post(
                url,
                json={
                    "event_type": event.event_type,
                    "title": event.title,
                    "message": event.message,
                    "priority": event.priority,
                    "tags": list(event.tags),
                },
                headers=headers,
                timeout=10,
            )
            if response.status_code >= 400:
                return DeliveryResult(
                    status=NotificationDeliveryStatus.FAILED,
                    response_code=response.status_code,
                    error_message=response.text,
                )
            return DeliveryResult(
                status=NotificationDeliveryStatus.SENT,
                response_code=response.status_code,
            )
        except httpx.HTTPError as exc:
            return DeliveryResult(
                status=NotificationDeliveryStatus.FAILED,
                response_code=(
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else None
                ),
                error_message=str(exc),
            )

    def _post_text(
        self,
        url: str,
        message: str,
        headers: dict[str, str],
    ) -> DeliveryResult:
        try:
            response = httpx.post(
                url,
                content=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            if response.status_code >= 400:
                return DeliveryResult(
                    status=NotificationDeliveryStatus.FAILED,
                    response_code=response.status_code,
                    error_message=response.text,
                )
            return DeliveryResult(
                status=NotificationDeliveryStatus.SENT,
                response_code=response.status_code,
            )
        except httpx.HTTPError as exc:
            return DeliveryResult(
                status=NotificationDeliveryStatus.FAILED,
                response_code=(
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else None
                ),
                error_message=str(exc),
            )

    def _get_channel(self, channel_uuid: str) -> NotificationChannel:
        channel = self.channel_repository.get_by_uuid(channel_uuid)
        if channel is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification channel not found.",
            )
        return channel

    def _channel_to_response(
        self,
        channel: NotificationChannel,
    ) -> NotificationChannelResponse:
        return NotificationChannelResponse(
            uuid=channel.uuid,
            name=channel.name,
            driver=NotificationDriver(channel.driver),
            enabled=channel.enabled,
            config=self._public_config(channel),
            created_at=channel.created_at,
            updated_at=channel.updated_at,
        )

    def _delivery_to_response(
        self,
        delivery: NotificationDelivery,
    ) -> NotificationDeliveryResponse:
        return NotificationDeliveryResponse(
            uuid=delivery.uuid,
            channel_uuid=delivery.channel.uuid,
            channel_name=delivery.channel.name,
            driver=NotificationDriver(delivery.channel.driver),
            event_type=delivery.event_type,
            status=NotificationDeliveryStatus(delivery.status),
            title=delivery.title,
            message=delivery.message,
            response_code=delivery.response_code,
            error_message=delivery.error_message,
            sent_at=delivery.sent_at,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
        )

    def _public_config(self, channel: NotificationChannel) -> dict[str, Any]:
        config = dict(channel.config)
        if "token" in config:
            config["token"] = "configured"
        return config
