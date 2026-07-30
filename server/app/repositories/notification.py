from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import NotificationChannel, NotificationDelivery


class NotificationChannelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[NotificationChannel]:
        return list(
            self.session.scalars(
                select(NotificationChannel).order_by(NotificationChannel.name)
            )
        )

    def list_enabled(self) -> list[NotificationChannel]:
        return list(
            self.session.scalars(
                select(NotificationChannel)
                .where(NotificationChannel.enabled.is_(True))
                .order_by(NotificationChannel.name)
            )
        )

    def get_by_uuid(self, channel_uuid: str) -> NotificationChannel | None:
        return self.session.scalar(
            select(NotificationChannel).where(NotificationChannel.uuid == channel_uuid)
        )

    def get_by_name(self, name: str) -> NotificationChannel | None:
        return self.session.scalar(
            select(NotificationChannel).where(NotificationChannel.name == name)
        )

    def add(self, channel: NotificationChannel) -> NotificationChannel:
        self.session.add(channel)
        self.session.flush()
        self.session.refresh(channel)
        return channel

    def delete(self, channel: NotificationChannel) -> None:
        self.session.delete(channel)
        self.session.flush()


class NotificationDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[NotificationDelivery]:
        return list(
            self.session.scalars(
                select(NotificationDelivery).order_by(
                    NotificationDelivery.created_at.desc()
                )
            )
        )

    def add(self, delivery: NotificationDelivery) -> NotificationDelivery:
        self.session.add(delivery)
        self.session.flush()
        self.session.refresh(delivery)
        return delivery
