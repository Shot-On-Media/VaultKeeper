from __future__ import annotations

import subprocess
from pathlib import Path

import pymysql
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.drivers.snapshot.mariadb import MariaDBConnectionConfig, MariaDBSnapshotDriver
from app.repositories.repository import RepositoryRepository
from app.schemas.mariadb_backup import MariaDBBackupCreate, MariaDBBackupResponse
from app.schemas.snapshot import SnapshotComplete, SnapshotCreate, SnapshotFail
from app.services.checksum import sha256_file
from app.services.repository import REPOSITORY_DIRECTORIES
from app.services.snapshot import SnapshotService


class MariaDBBackupService:
    def __init__(self, session: Session) -> None:
        settings = get_settings()
        self.connection_config = MariaDBConnectionConfig(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
        )
        self.default_database_name = settings.db_name
        self.driver = MariaDBSnapshotDriver()
        self.repository_repository = RepositoryRepository(session)
        self.snapshot_service = SnapshotService(session)

    def discover_databases(self) -> list[str]:
        try:
            return self.driver.discover_databases(self.connection_config)
        except pymysql.MySQLError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MariaDB database discovery failed.",
            ) from exc

    def run_backup(self, payload: MariaDBBackupCreate) -> MariaDBBackupResponse:
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

        database_name = payload.database_name or self.default_database_name
        snapshot = self.snapshot_service.register_snapshot(
            SnapshotCreate(
                repository_uuid=payload.repository_uuid,
                engine="mariadb",
                source=database_name,
                manifest={},
            )
        )
        snapshot = self.snapshot_service.start_snapshot(snapshot.uuid)
        dump_path = snapshots_path / f"{snapshot.uuid}.sql"
        artifact_path = snapshots_path / f"{snapshot.uuid}.sql.zst"

        try:
            self.driver.dump_database(self.connection_config, database_name, dump_path)
            dump_bytes = dump_path.stat().st_size
            self.driver.compress_zstd(dump_path, artifact_path)
            dump_path.unlink()
            compressed_bytes = artifact_path.stat().st_size
            checksum = sha256_file(artifact_path)
            snapshot = self.snapshot_service.complete_snapshot(
                snapshot.uuid,
                SnapshotComplete(
                    size_bytes=compressed_bytes,
                    manifest={
                        "artifact": artifact_path.name,
                        "compression": "zstd",
                        "database": database_name,
                        "format": "sql",
                        "sha256": checksum,
                        "source_bytes": dump_bytes,
                    },
                ),
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            if dump_path.exists():
                dump_path.unlink()
            if artifact_path.exists():
                artifact_path.unlink()
            self.snapshot_service.fail_snapshot(
                snapshot.uuid,
                SnapshotFail(failure_message=str(exc)),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MariaDB backup failed.",
            ) from exc

        return MariaDBBackupResponse(
            snapshot=snapshot,
            artifact_path=str(artifact_path),
            database_name=database_name,
            dump_bytes=dump_bytes,
            compressed_bytes=compressed_bytes,
        )

    def _repository_layout_exists(self, repository_path: Path) -> bool:
        required_paths = ("repository.json", *REPOSITORY_DIRECTORIES)
        return repository_path.is_dir() and all(
            (repository_path / name).exists() for name in required_paths
        )
