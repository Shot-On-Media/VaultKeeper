from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pymysql
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.drivers.snapshot.mariadb import MariaDBConnectionConfig, MariaDBSnapshotDriver
from app.drivers.ssh import OpenSSHDriver, SSHHostKeyResult
from app.models.managed_server import ManagedServer
from app.repositories.managed_server import ManagedServerRepository
from app.repositories.repository import RepositoryRepository
from app.schemas.managed_server import ManagedServerStatus
from app.schemas.mariadb_backup import MariaDBBackupCreate, MariaDBBackupResponse
from app.schemas.snapshot import SnapshotComplete, SnapshotCreate, SnapshotFail
from app.services.checksum import sha256_file
from app.services.repository import REPOSITORY_DIRECTORIES
from app.services.snapshot import SnapshotService


class MariaDBBackupService:
    def __init__(
        self,
        session: Session,
        ssh_driver: OpenSSHDriver | None = None,
    ) -> None:
        settings = get_settings()
        self.connection_config = MariaDBConnectionConfig(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
        )
        self.default_database_name = settings.db_name
        self.driver = MariaDBSnapshotDriver()
        self.ssh_driver = ssh_driver or OpenSSHDriver()
        self.managed_server_repository = ManagedServerRepository(session)
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

        if payload.managed_server_uuid is not None:
            return self._run_remote_backup(payload, snapshots_path)
        return self._run_local_backup(payload, snapshots_path)

    def _run_local_backup(
        self,
        payload: MariaDBBackupCreate,
        snapshots_path: Path,
    ) -> MariaDBBackupResponse:
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

    def _run_remote_backup(
        self,
        payload: MariaDBBackupCreate,
        snapshots_path: Path,
    ) -> MariaDBBackupResponse:
        server = self._get_managed_server(payload.managed_server_uuid)
        host_key = self._scan_trusted_host_key(server)
        database_name = payload.database_name or self.default_database_name
        snapshot = self.snapshot_service.register_snapshot(
            SnapshotCreate(
                repository_uuid=payload.repository_uuid,
                engine="mariadb",
                source=f"{server.name}:{database_name}",
                manifest={
                    "database": database_name,
                    "managed_server_uuid": server.uuid,
                    "remote_hostname": server.hostname,
                },
            )
        )
        snapshot = self.snapshot_service.start_snapshot(snapshot.uuid)
        artifact_path = snapshots_path / f"{snapshot.uuid}.sql.zst"
        try:
            result = self.ssh_driver.stream_checked_binary_command(
                server.hostname,
                server.ssh_port,
                server.ssh_username,
                host_key,
                [
                    server.client_path,
                    "mariadb-snapshot",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.connection_config.port),
                    "--user",
                    self.connection_config.user,
                    "--password",
                    self.connection_config.password,
                    "--database",
                    database_name,
                ],
                artifact_path,
            )
            if result.exit_code != 0:
                raise RuntimeError(result.stderr.strip() or "Remote backup failed.")
            metadata = self._parse_remote_metadata(result.stderr)
            dump_bytes = self._metadata_int(metadata, "source_bytes")
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
                        "managed_server_uuid": server.uuid,
                        "remote_hostname": server.hostname,
                        "sha256": checksum,
                        "source_bytes": dump_bytes,
                    },
                ),
            )
        except (OSError, RuntimeError) as exc:
            if artifact_path.exists():
                artifact_path.unlink()
            self.snapshot_service.fail_snapshot(
                snapshot.uuid,
                SnapshotFail(failure_message=str(exc)),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Remote MariaDB backup failed.",
            ) from exc
        return MariaDBBackupResponse(
            snapshot=snapshot,
            artifact_path=str(artifact_path),
            database_name=database_name,
            dump_bytes=dump_bytes,
            compressed_bytes=compressed_bytes,
        )

    def _get_managed_server(self, server_uuid: str | None) -> ManagedServer:
        if server_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Managed server is required.",
            )
        server = self.managed_server_repository.get_by_uuid(server_uuid)
        if server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Managed server not found.",
            )
        return server

    def _scan_trusted_host_key(self, server: ManagedServer) -> SSHHostKeyResult:
        try:
            host_key = self.ssh_driver.scan_host_key(server.hostname, server.ssh_port)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        if server.ssh_host_key_sha256 != host_key.fingerprint_sha256:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SSH host key is not trusted: {host_key.fingerprint_sha256}",
            )
        server.status = ManagedServerStatus.ONLINE.value
        return host_key

    def _parse_remote_metadata(self, stderr: str) -> dict[str, Any]:
        try:
            parsed = json.loads(stderr.strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError("Remote backup metadata was invalid.") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Remote backup metadata was invalid.")
        return parsed

    def _metadata_int(self, metadata: dict[str, Any], key: str) -> int:
        value = metadata.get(key)
        if isinstance(value, int):
            return value
        raise RuntimeError(f"Remote backup metadata missing {key}.")

    def _repository_layout_exists(self, repository_path: Path) -> bool:
        required_paths = ("repository.json", *REPOSITORY_DIRECTORIES)
        return repository_path.is_dir() and all(
            (repository_path / name).exists() for name in required_paths
        )
