from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.drivers.snapshot.filesystem import FilesystemSnapshotDriver
from app.repositories.repository import RepositoryRepository
from app.schemas.filesystem_backup import (
    FilesystemBackupCreate,
    FilesystemBackupResponse,
)
from app.schemas.snapshot import SnapshotComplete, SnapshotCreate, SnapshotFail
from app.services.checksum import sha256_file
from app.services.repository import REPOSITORY_DIRECTORIES
from app.services.snapshot import SnapshotService


class FilesystemBackupService:
    def __init__(self, session: Session) -> None:
        self.repository_repository = RepositoryRepository(session)
        self.snapshot_service = SnapshotService(session)
        self.driver = FilesystemSnapshotDriver()

    def run_backup(self, payload: FilesystemBackupCreate) -> FilesystemBackupResponse:
        repository = self.repository_repository.get_by_uuid(payload.repository_uuid)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found.",
            )

        repository_path = Path(repository.path)
        snapshots_path = repository_path / "snapshots"
        if not self._repository_layout_exists(repository_path):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Repository layout is incomplete.",
            )

        source_path = Path(payload.source_path)
        if not source_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Source path does not exist or is not a directory.",
            )

        snapshot = self.snapshot_service.register_snapshot(
            SnapshotCreate(
                repository_uuid=payload.repository_uuid,
                engine="filesystem",
                source=str(source_path),
                manifest={},
            )
        )
        snapshot = self.snapshot_service.start_snapshot(snapshot.uuid)
        tar_path = snapshots_path / f"{snapshot.uuid}.tar"
        artifact_path = snapshots_path / f"{snapshot.uuid}.tar.zst"

        try:
            scan_result = self.driver.scan(source_path)
            self.driver.create_tar(source_path, tar_path)
            self.driver.compress_zstd(tar_path, artifact_path)
            tar_path.unlink()
            compressed_bytes = artifact_path.stat().st_size
            checksum = sha256_file(artifact_path)
            snapshot = self.snapshot_service.complete_snapshot(
                snapshot.uuid,
                SnapshotComplete(
                    size_bytes=compressed_bytes,
                    manifest={
                        "artifact": artifact_path.name,
                        "compression": "zstd",
                        "format": "tar",
                        "file_count": scan_result.file_count,
                        "sha256": checksum,
                        "source_bytes": scan_result.total_bytes,
                    },
                ),
            )
        except OSError as exc:
            if tar_path.exists():
                tar_path.unlink()
            if artifact_path.exists():
                artifact_path.unlink()
            self.snapshot_service.fail_snapshot(
                snapshot.uuid,
                SnapshotFail(failure_message=str(exc)),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Filesystem backup failed.",
            ) from exc

        return FilesystemBackupResponse(
            snapshot=snapshot,
            artifact_path=str(artifact_path),
            file_count=scan_result.file_count,
            source_bytes=scan_result.total_bytes,
            compressed_bytes=compressed_bytes,
        )

    def _repository_layout_exists(self, repository_path: Path) -> bool:
        required_paths = ("repository.json", *REPOSITORY_DIRECTORIES)
        return repository_path.is_dir() and all(
            (repository_path / name).exists() for name in required_paths
        )
