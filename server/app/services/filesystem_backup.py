from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.drivers.snapshot.filesystem import FilesystemSnapshotDriver
from app.drivers.ssh import OpenSSHDriver, SSHHostKeyResult
from app.models.managed_server import ManagedServer
from app.repositories.managed_server import ManagedServerRepository
from app.repositories.repository import RepositoryRepository
from app.schemas.filesystem_backup import (
    FilesystemBackupCreate,
    FilesystemBackupResponse,
)
from app.schemas.managed_server import ManagedServerStatus
from app.schemas.snapshot import SnapshotComplete, SnapshotCreate, SnapshotFail
from app.services.checksum import sha256_file
from app.services.repository import REPOSITORY_DIRECTORIES
from app.services.snapshot import SnapshotService


class FilesystemBackupService:
    def __init__(
        self,
        session: Session,
        ssh_driver: OpenSSHDriver | None = None,
    ) -> None:
        self.repository_repository = RepositoryRepository(session)
        self.managed_server_repository = ManagedServerRepository(session)
        self.snapshot_service = SnapshotService(session)
        self.driver = FilesystemSnapshotDriver()
        self.ssh_driver = ssh_driver or OpenSSHDriver()

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

        if payload.managed_server_uuid is not None:
            return self._run_remote_backup(payload, snapshots_path)
        return self._run_local_backup(payload, snapshots_path)

    def _run_local_backup(
        self,
        payload: FilesystemBackupCreate,
        snapshots_path: Path,
    ) -> FilesystemBackupResponse:
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

    def _run_remote_backup(
        self,
        payload: FilesystemBackupCreate,
        snapshots_path: Path,
    ) -> FilesystemBackupResponse:
        server = self._get_managed_server(payload.managed_server_uuid)
        host_key = self._scan_trusted_host_key(server)
        snapshot = self.snapshot_service.register_snapshot(
            SnapshotCreate(
                repository_uuid=payload.repository_uuid,
                engine="filesystem",
                source=f"{server.name}:{payload.source_path}",
                manifest={
                    "managed_server_uuid": server.uuid,
                    "remote_hostname": server.hostname,
                },
            )
        )
        snapshot = self.snapshot_service.start_snapshot(snapshot.uuid)
        artifact_path = snapshots_path / f"{snapshot.uuid}.tar.zst"
        try:
            result = self.ssh_driver.stream_checked_binary_command(
                server.hostname,
                server.ssh_port,
                server.ssh_username,
                host_key,
                [
                    server.client_path,
                    "filesystem-snapshot",
                    payload.source_path,
                ],
                artifact_path,
            )
            if result.exit_code != 0:
                raise RuntimeError(result.stderr.strip() or "Remote backup failed.")
            metadata = self._parse_remote_metadata(result.stderr)
            compressed_bytes = artifact_path.stat().st_size
            checksum = sha256_file(artifact_path)
            file_count = self._metadata_int(metadata, "file_count")
            source_bytes = self._metadata_int(metadata, "source_bytes")
            snapshot = self.snapshot_service.complete_snapshot(
                snapshot.uuid,
                SnapshotComplete(
                    size_bytes=compressed_bytes,
                    manifest={
                        "artifact": artifact_path.name,
                        "compression": "zstd",
                        "format": "tar",
                        "file_count": file_count,
                        "managed_server_uuid": server.uuid,
                        "remote_hostname": server.hostname,
                        "sha256": checksum,
                        "source_bytes": source_bytes,
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
                detail="Remote filesystem backup failed.",
            ) from exc
        return FilesystemBackupResponse(
            snapshot=snapshot,
            artifact_path=str(artifact_path),
            file_count=file_count,
            source_bytes=source_bytes,
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
