from __future__ import annotations

import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import zstandard
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.restore import RestoreJob
from app.models.snapshot import Snapshot
from app.repositories.restore import RestoreJobRepository
from app.repositories.snapshot import SnapshotRepository
from app.schemas.restore import RestoreCreate, RestoreResponse, RestoreStatus
from app.schemas.snapshot import SnapshotStatus
from app.services.notification import NotificationEvent, NotificationService

logger = structlog.get_logger(__name__)


class RestoreService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.restore_repository = RestoreJobRepository(session)
        self.snapshot_repository = SnapshotRepository(session)

    def list_restores(self) -> list[RestoreResponse]:
        return [
            self._to_response(restore_job)
            for restore_job in self.restore_repository.list()
        ]

    def restore_snapshot(self, payload: RestoreCreate) -> RestoreResponse:
        snapshot = self.snapshot_repository.get_by_uuid(payload.snapshot_uuid)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found.",
            )
        if SnapshotStatus(snapshot.status) is not SnapshotStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only completed snapshots can be restored.",
            )

        restore_job = RestoreJob(
            snapshot_id=snapshot.id,
            status=RestoreStatus.REQUESTED.value,
            target_path=payload.target_path,
            progress_percent=0,
        )
        self.restore_repository.add(restore_job)
        self.session.commit()
        self.session.refresh(restore_job)

        logger.info(
            "restore_requested",
            restore_uuid=restore_job.uuid,
            snapshot_uuid=snapshot.uuid,
            engine=snapshot.engine,
            target_path=restore_job.target_path,
        )

        try:
            self._mark_running(restore_job)
            artifact_path = self._artifact_path(snapshot)
            if snapshot.engine == "filesystem":
                message = self._restore_filesystem_snapshot(
                    snapshot,
                    artifact_path,
                    payload,
                )
            elif snapshot.engine == "mariadb":
                message = self._stage_mariadb_snapshot(snapshot, artifact_path, payload)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Snapshot engine is not restorable.",
                )
            self._mark_completed(restore_job, message)
        except HTTPException as exc:
            self._mark_failed(restore_job, str(exc.detail))
            raise
        except (OSError, tarfile.TarError, zstandard.ZstdError) as exc:
            self._mark_failed(restore_job, str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Restore failed.",
            ) from exc

        self.session.refresh(restore_job)
        return self._to_response(restore_job)

    def _mark_running(self, restore_job: RestoreJob) -> None:
        restore_job.status = RestoreStatus.RUNNING.value
        restore_job.progress_percent = 10
        restore_job.started_at = datetime.now(UTC)
        self.session.commit()
        logger.info("restore_started", restore_uuid=restore_job.uuid)

    def _mark_completed(self, restore_job: RestoreJob, message: str) -> None:
        restore_job.status = RestoreStatus.COMPLETED.value
        restore_job.progress_percent = 100
        restore_job.verification_message = message
        restore_job.error_message = None
        restore_job.completed_at = datetime.now(UTC)
        self.session.commit()
        logger.info("restore_completed", restore_uuid=restore_job.uuid)

    def _mark_failed(self, restore_job: RestoreJob, message: str) -> None:
        restore_job.status = RestoreStatus.FAILED.value
        restore_job.error_message = message
        restore_job.completed_at = datetime.now(UTC)
        self.session.commit()
        logger.warning(
            "restore_failed",
            restore_uuid=restore_job.uuid,
            error_message=message,
        )
        NotificationService(self.session).notify_event(
            NotificationEvent(
                event_type="restore.failed",
                title="VaultKeeper restore failed",
                message=(
                    f"Restore {restore_job.uuid} for snapshot "
                    f"{restore_job.snapshot.uuid} failed: {message}"
                ),
                priority="high",
                tags=("warning",),
            )
        )

    def _artifact_path(self, snapshot: Snapshot) -> Path:
        manifest = snapshot.manifest
        artifact_name = manifest.get("artifact")
        if not isinstance(artifact_name, str) or artifact_name == "":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Snapshot manifest does not include an artifact.",
            )

        artifact_path = Path(snapshot.repository.path) / "snapshots" / artifact_name
        if not artifact_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Snapshot artifact is missing.",
            )
        return artifact_path

    def _restore_filesystem_snapshot(
        self,
        snapshot: Snapshot,
        artifact_path: Path,
        payload: RestoreCreate,
    ) -> str:
        manifest = snapshot.manifest
        self._require_manifest_value(manifest, "compression", "zstd")
        self._require_manifest_value(manifest, "format", "tar")

        target_path = Path(payload.target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        temp_tar_path = target_path / f".{snapshot.uuid}.restore.tar"

        self._decompress_zstd(artifact_path, temp_tar_path)
        try:
            with tarfile.open(temp_tar_path, mode="r") as archive:
                self._safe_extract(archive, target_path)
        finally:
            if temp_tar_path.exists():
                temp_tar_path.unlink()

        file_count = sum(1 for path in target_path.rglob("*") if path.is_file())
        return f"Filesystem snapshot restored with {file_count} files."

    def _stage_mariadb_snapshot(
        self,
        snapshot: Snapshot,
        artifact_path: Path,
        payload: RestoreCreate,
    ) -> str:
        manifest = snapshot.manifest
        self._require_manifest_value(manifest, "compression", "zstd")
        self._require_manifest_value(manifest, "format", "sql")

        target_path = Path(payload.target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        database_name = manifest.get("database")
        if not isinstance(database_name, str) or database_name == "":
            database_name = snapshot.source
        staged_path = target_path / f"{database_name}-{snapshot.uuid}.sql"
        self._decompress_zstd(artifact_path, staged_path)
        return f"MariaDB dump staged at {staged_path}."

    def _decompress_zstd(self, artifact_path: Path, destination_path: Path) -> None:
        decompressor = zstandard.ZstdDecompressor()
        with artifact_path.open("rb") as source_file:
            with destination_path.open("wb") as destination_file:
                decompressor.copy_stream(source_file, destination_file)

    def _safe_extract(self, archive: tarfile.TarFile, target_path: Path) -> None:
        resolved_target = target_path.resolve()
        for member in archive.getmembers():
            member_path = (target_path / member.name).resolve()
            if (
                resolved_target != member_path
                and resolved_target not in member_path.parents
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Snapshot archive contains an unsafe path.",
                )
        archive.extractall(target_path, filter="data")

    def _require_manifest_value(
        self,
        manifest: dict[str, Any],
        key: str,
        expected: str,
    ) -> None:
        if manifest.get(key) != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Snapshot manifest must use {expected} {key}.",
            )

    def _to_response(self, restore_job: RestoreJob) -> RestoreResponse:
        return RestoreResponse(
            uuid=restore_job.uuid,
            snapshot_uuid=restore_job.snapshot.uuid,
            status=RestoreStatus(restore_job.status),
            target_path=restore_job.target_path,
            progress_percent=restore_job.progress_percent,
            verification_message=restore_job.verification_message,
            error_message=restore_job.error_message,
            started_at=restore_job.started_at,
            completed_at=restore_job.completed_at,
            created_at=restore_job.created_at,
            updated_at=restore_job.updated_at,
        )
