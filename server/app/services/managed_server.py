from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.managed_server import ManagedServer
from app.repositories.managed_server import ManagedServerRepository
from app.schemas.managed_server import (
    ManagedServerCreate,
    ManagedServerResponse,
    ManagedServerStatus,
    ManagedServerUpdate,
)


class ManagedServerService:
    def __init__(self, session: Session) -> None:
        self.repository = ManagedServerRepository(session)
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
