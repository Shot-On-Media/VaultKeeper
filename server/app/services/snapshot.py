from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.snapshot import Snapshot
from app.repositories.repository import RepositoryRepository
from app.repositories.snapshot import SnapshotRepository
from app.schemas.snapshot import (
    SnapshotComplete,
    SnapshotCreate,
    SnapshotFail,
    SnapshotResponse,
    SnapshotStatus,
)


class SnapshotService:
    def __init__(self, session: Session) -> None:
        self.repository_repository = RepositoryRepository(session)
        self.snapshot_repository = SnapshotRepository(session)
        self.session = session

    def list_snapshots(
        self,
        repository_uuid: str | None = None,
    ) -> list[SnapshotResponse]:
        return [
            self._to_response(snapshot)
            for snapshot in self.snapshot_repository.list(repository_uuid)
        ]

    def register_snapshot(self, payload: SnapshotCreate) -> SnapshotResponse:
        repository = self.repository_repository.get_by_uuid(payload.repository_uuid)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found.",
            )

        snapshot = Snapshot(
            repository_id=repository.id,
            engine=payload.engine,
            source=payload.source,
            status=SnapshotStatus.PENDING.value,
            manifest=payload.manifest,
        )
        self.snapshot_repository.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return self._to_response(snapshot)

    def start_snapshot(self, snapshot_uuid: str) -> SnapshotResponse:
        snapshot = self._get_snapshot(snapshot_uuid)
        if SnapshotStatus(snapshot.status) is not SnapshotStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending snapshots can be started.",
            )

        snapshot.status = SnapshotStatus.RUNNING.value
        snapshot.started_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(snapshot)
        return self._to_response(snapshot)

    def complete_snapshot(
        self,
        snapshot_uuid: str,
        payload: SnapshotComplete,
    ) -> SnapshotResponse:
        snapshot = self._get_snapshot(snapshot_uuid)
        if SnapshotStatus(snapshot.status) is not SnapshotStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only running snapshots can be completed.",
            )

        snapshot.status = SnapshotStatus.COMPLETED.value
        snapshot.completed_at = datetime.now(UTC)
        snapshot.size_bytes = payload.size_bytes
        snapshot.manifest = payload.manifest
        snapshot.failure_message = None
        self.session.commit()
        self.session.refresh(snapshot)
        return self._to_response(snapshot)

    def fail_snapshot(
        self,
        snapshot_uuid: str,
        payload: SnapshotFail,
    ) -> SnapshotResponse:
        snapshot = self._get_snapshot(snapshot_uuid)
        if SnapshotStatus(snapshot.status) is SnapshotStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Completed snapshots cannot be failed.",
            )

        snapshot.status = SnapshotStatus.FAILED.value
        snapshot.completed_at = datetime.now(UTC)
        snapshot.failure_message = payload.failure_message
        self.session.commit()
        self.session.refresh(snapshot)
        return self._to_response(snapshot)

    def _get_snapshot(self, snapshot_uuid: str) -> Snapshot:
        snapshot = self.snapshot_repository.get_by_uuid(snapshot_uuid)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found.",
            )
        return snapshot

    def _to_response(self, snapshot: Snapshot) -> SnapshotResponse:
        return SnapshotResponse(
            uuid=snapshot.uuid,
            repository_uuid=snapshot.repository.uuid,
            engine=snapshot.engine,
            source=snapshot.source,
            status=SnapshotStatus(snapshot.status),
            size_bytes=snapshot.size_bytes,
            manifest=snapshot.manifest,
            started_at=snapshot.started_at,
            completed_at=snapshot.completed_at,
            failure_message=snapshot.failure_message,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
        )
