from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository


class RepositoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Repository]:
        return list(self.session.scalars(select(Repository).order_by(Repository.name)))

    def get_by_uuid(self, repository_uuid: str) -> Repository | None:
        return self.session.scalar(
            select(Repository).where(Repository.uuid == repository_uuid)
        )

    def get_by_name(self, name: str) -> Repository | None:
        return self.session.scalar(select(Repository).where(Repository.name == name))

    def list_by_storage_uuid(self, storage_uuid: str) -> list[Repository]:
        return list(
            self.session.scalars(
                select(Repository).where(
                    Repository.storage.has(uuid=storage_uuid),
                )
            )
        )

    def add(self, repository: Repository) -> Repository:
        self.session.add(repository)
        self.session.flush()
        self.session.refresh(repository)
        return repository

    def delete(self, repository: Repository) -> None:
        self.session.delete(repository)
        self.session.flush()
