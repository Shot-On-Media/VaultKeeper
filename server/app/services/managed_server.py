from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.drivers.ssh import OpenSSHDriver
from app.models.managed_server import ManagedServer
from app.repositories.managed_server import ManagedServerRepository
from app.schemas.managed_server import (
    ManagedServerConnectivityResponse,
    ManagedServerCreate,
    ManagedServerHostKeyResponse,
    ManagedServerResponse,
    ManagedServerStatus,
    ManagedServerUpdate,
)


class ManagedServerService:
    def __init__(
        self, session: Session, ssh_driver: OpenSSHDriver | None = None
    ) -> None:
        self.repository = ManagedServerRepository(session)
        self.ssh_driver = ssh_driver or OpenSSHDriver()
        self.session = session

    def list_servers(self) -> list[ManagedServerResponse]:
        return [self._to_response(server) for server in self.repository.list()]

    def create_server(self, payload: ManagedServerCreate) -> ManagedServerResponse:
        if self.repository.get_by_name(payload.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Managed server name already exists.",
            )
        server = ManagedServer(
            name=payload.name,
            hostname=payload.hostname,
            ssh_port=payload.ssh_port,
            ssh_username=payload.ssh_username,
            ssh_host_key_sha256=payload.ssh_host_key_sha256,
            client_path=payload.client_path,
            tags=payload.tags,
            status=ManagedServerStatus.UNKNOWN.value,
        )
        self.repository.add(server)
        self.session.commit()
        self.session.refresh(server)
        return self._to_response(server)

    def update_server(
        self,
        server_uuid: str,
        payload: ManagedServerUpdate,
    ) -> ManagedServerResponse:
        server = self._get_server(server_uuid)
        if payload.name is not None and payload.name != server.name:
            if self.repository.get_by_name(payload.name) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Managed server name already exists.",
                )
            server.name = payload.name
        if payload.hostname is not None:
            server.hostname = payload.hostname
        if payload.ssh_port is not None:
            server.ssh_port = payload.ssh_port
        if payload.ssh_username is not None:
            server.ssh_username = payload.ssh_username
        if payload.ssh_host_key_sha256 is not None:
            server.ssh_host_key_sha256 = payload.ssh_host_key_sha256
        if payload.client_path is not None:
            server.client_path = payload.client_path
        if payload.tags is not None:
            server.tags = payload.tags
        self.session.commit()
        self.session.refresh(server)
        return self._to_response(server)

    def delete_server(self, server_uuid: str) -> None:
        server = self._get_server(server_uuid)
        self.repository.delete(server)
        self.session.commit()

    def verify_host_key(self, server_uuid: str) -> ManagedServerHostKeyResponse:
        server = self._get_server(server_uuid)
        checked_at = datetime.now(UTC)
        try:
            host_key = self.ssh_driver.scan_host_key(server.hostname, server.ssh_port)
        except RuntimeError as exc:
            server.status = ManagedServerStatus.OFFLINE.value
            server.last_checked_at = checked_at
            server.last_error = str(exc)
            self.session.commit()
            return ManagedServerHostKeyResponse(
                uuid=server.uuid,
                fingerprint_sha256="",
                trusted=False,
                message=str(exc),
                checked_at=checked_at,
            )

        server.ssh_host_key_sha256 = host_key.fingerprint_sha256
        server.status = ManagedServerStatus.UNKNOWN.value
        server.last_checked_at = checked_at
        server.last_error = None
        self.session.commit()
        return ManagedServerHostKeyResponse(
            uuid=server.uuid,
            fingerprint_sha256=host_key.fingerprint_sha256,
            trusted=True,
            message="SSH host key fingerprint trusted.",
            checked_at=checked_at,
        )

    def test_connectivity(
        self,
        server_uuid: str,
    ) -> ManagedServerConnectivityResponse:
        server = self._get_server(server_uuid)
        checked_at = datetime.now(UTC)
        try:
            host_key = self.ssh_driver.scan_host_key(server.hostname, server.ssh_port)
        except RuntimeError as exc:
            return self._record_connectivity_result(
                server,
                ManagedServerStatus.OFFLINE,
                False,
                str(exc),
                checked_at,
            )
        if server.ssh_host_key_sha256 != host_key.fingerprint_sha256:
            return self._record_connectivity_result(
                server,
                ManagedServerStatus.UNVERIFIED,
                False,
                f"SSH host key is not trusted: {host_key.fingerprint_sha256}",
                checked_at,
            )
        result = self.ssh_driver.run_checked_command(
            server.hostname,
            server.ssh_port,
            server.ssh_username,
            host_key,
            ["true"],
        )
        if result.exit_code != 0:
            return self._record_connectivity_result(
                server,
                ManagedServerStatus.OFFLINE,
                True,
                result.stderr.strip() or "SSH connectivity test failed.",
                checked_at,
            )
        return self._record_connectivity_result(
            server,
            ManagedServerStatus.ONLINE,
            True,
            "SSH connectivity verified.",
            checked_at,
        )

    def _record_connectivity_result(
        self,
        server: ManagedServer,
        status_value: ManagedServerStatus,
        host_key_verified: bool,
        message: str,
        checked_at: datetime,
    ) -> ManagedServerConnectivityResponse:
        server.status = status_value.value
        server.last_checked_at = checked_at
        server.last_error = (
            None if status_value is ManagedServerStatus.ONLINE else message
        )
        self.session.commit()
        return ManagedServerConnectivityResponse(
            uuid=server.uuid,
            status=status_value,
            host_key_verified=host_key_verified,
            message=message,
            checked_at=checked_at,
        )

    def _get_server(self, server_uuid: str) -> ManagedServer:
        server = self.repository.get_by_uuid(server_uuid)
        if server is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Managed server not found.",
            )
        return server

    def _to_response(self, server: ManagedServer) -> ManagedServerResponse:
        return ManagedServerResponse(
            uuid=server.uuid,
            name=server.name,
            hostname=server.hostname,
            ssh_port=server.ssh_port,
            ssh_username=server.ssh_username,
            ssh_host_key_sha256=server.ssh_host_key_sha256,
            client_path=server.client_path,
            tags=server.tags,
            status=ManagedServerStatus(server.status),
            last_checked_at=server.last_checked_at,
            last_error=server.last_error,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )
