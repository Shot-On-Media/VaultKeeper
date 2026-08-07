from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.storage import Storage


class StorageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Storage]:
        return list(self.session.scalars(select(Storage).order_by(Storage.name)))

    def get_by_uuid(self, storage_uuid: str) -> Storage | None:
        return self.session.scalar(select(Storage).where(Storage.uuid == storage_uuid))

    def get_by_name(self, name: str) -> Storage | None:
        return self.session.scalar(select(Storage).where(Storage.name == name))

    def add(self, storage: Storage) -> Storage:
        self.session.add(storage)
        self.session.flush()
        self.session.refresh(storage)
        return storage

    def delete(self, storage: Storage) -> None:
        self.session.delete(storage)
        self.session.flush()
