from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.snapshot import Snapshot


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, repository_uuid: str | None = None) -> list[Snapshot]:
        statement = select(Snapshot).order_by(Snapshot.created_at.desc())
        if repository_uuid is not None:
            statement = statement.join(Snapshot.repository).where(
                Snapshot.repository.has(uuid=repository_uuid)
            )
        return list(self.session.scalars(statement))

    def get_by_uuid(self, snapshot_uuid: str) -> Snapshot | None:
        return self.session.scalar(
            select(Snapshot).where(Snapshot.uuid == snapshot_uuid)
        )

    def add(self, snapshot: Snapshot) -> Snapshot:
        self.session.add(snapshot)
        self.session.flush()
        self.session.refresh(snapshot)
        return snapshot
