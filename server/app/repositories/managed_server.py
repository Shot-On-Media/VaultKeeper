from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.managed_server import ManagedServer


class ManagedServerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[ManagedServer]:
        return list(
            self.session.scalars(select(ManagedServer).order_by(ManagedServer.name))
        )

    def get_by_uuid(self, server_uuid: str) -> ManagedServer | None:
        return self.session.scalar(
            select(ManagedServer).where(ManagedServer.uuid == server_uuid)
        )

    def get_by_name(self, name: str) -> ManagedServer | None:
        return self.session.scalar(
            select(ManagedServer).where(ManagedServer.name == name)
        )

    def add(self, server: ManagedServer) -> ManagedServer:
        self.session.add(server)
        self.session.flush()
        self.session.refresh(server)
        return server

    def delete(self, server: ManagedServer) -> None:
        self.session.delete(server)
        self.session.flush()
