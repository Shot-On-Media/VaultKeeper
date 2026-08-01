from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.session import get_database_session
from app.drivers.ssh import SSHCommandResult, SSHHostKeyResult
from app.main import create_app
from app.models import ManagedServer

_ = ManagedServer


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=Session,
    )

    def override_database_session() -> Generator[Session]:
        with session_factory() as session:
            yield session

    app = create_app(
        Settings(
            db_name="vaultkeeper",
            db_user="vaultkeeper",
            db_password="vaultkeeper",
        )
    )
    app.dependency_overrides[get_database_session] = override_database_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_managed_server_crud(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Web 01",
            "hostname": "web01.example.test",
            "ssh_port": 2222,
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:abc123",
            "client_path": "/usr/local/bin/vaultkeeper",
            "tags": {"role": "web"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Web 01"
    assert created["hostname"] == "web01.example.test"
    assert created["ssh_port"] == 2222
    assert created["ssh_username"] == "vaultkeeper"
    assert created["ssh_host_key_sha256"] == "SHA256:abc123"
    assert created["client_path"] == "/usr/local/bin/vaultkeeper"
    assert created["tags"] == {"role": "web"}
    assert created["status"] == "unknown"

    list_response = client.get("/api/v1/managed-servers")

    assert list_response.status_code == 200
    assert [item["uuid"] for item in list_response.json()] == [created["uuid"]]

    update_response = client.put(
        f"/api/v1/managed-servers/{created['uuid']}",
        json={
            "name": "Web Primary",
            "hostname": "web-primary.example.test",
            "ssh_port": 22,
            "tags": {"role": "web", "tier": "primary"},
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Web Primary"
    assert updated["hostname"] == "web-primary.example.test"
    assert updated["ssh_port"] == 22
    assert updated["ssh_username"] == "vaultkeeper"
    assert updated["tags"] == {"role": "web", "tier": "primary"}

    delete_response = client.delete(f"/api/v1/managed-servers/{created['uuid']}")

    assert delete_response.status_code == 204
    assert client.get("/api/v1/managed-servers").json() == []


def test_managed_server_names_must_be_unique(client: TestClient) -> None:
    payload = {
        "name": "Database 01",
        "hostname": "db01.example.test",
        "ssh_username": "vaultkeeper",
    }

    assert client.post("/api/v1/managed-servers", json=payload).status_code == 201
    response = client.post("/api/v1/managed-servers", json=payload)

    assert response.status_code == 409


def test_managed_server_validates_ssh_port(client: TestClient) -> None:
    response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Invalid server",
            "hostname": "invalid.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_port": 70000,
        },
    )

    assert response.status_code == 422


def test_missing_managed_server_returns_404(client: TestClient) -> None:
    response = client.put(
        "/api/v1/managed-servers/00000000-0000-0000-0000-000000000000",
        json={"name": "Missing"},
    )

    assert response.status_code == 404


class FakeSuccessfulSSHDriver:
    def scan_host_key(self, hostname: str, port: int) -> SSHHostKeyResult:
        return SSHHostKeyResult(
            fingerprint_sha256="SHA256:trusted",
            known_hosts_entry=f"[{hostname}]:{port} ssh-ed25519 AAAA",
        )

    def run_checked_command(
        self,
        hostname: str,
        port: int,
        username: str,
        host_key: SSHHostKeyResult,
        command: list[str],
        timeout_seconds: int = 10,
    ) -> SSHCommandResult:
        if command[:2] == ["sh", "-c"]:
            return SSHCommandResult(
                exit_code=0,
                stdout=(
                    "os_id=debian\n"
                    "os_name=Debian GNU/Linux 12 (bookworm)\n"
                    "kernel=6.1.0\n"
                    "architecture=x86_64\n"
                    "cpu_count=4\n"
                    "memory_total_kib=8123456\n"
                    "root_total_kib=41234567\n"
                    "root_available_kib=21234567\n"
                    "python3_path=/usr/bin/python3\n"
                    "mariadb_path=/usr/bin/mariadb\n"
                    "rsync_path=\n"
                ),
                stderr="",
            )
        return SSHCommandResult(exit_code=0, stdout="", stderr="")


class FakeFailingSSHDriver:
    def scan_host_key(self, hostname: str, port: int) -> SSHHostKeyResult:
        raise RuntimeError("connection timed out")


class FakeFailingInventorySSHDriver(FakeSuccessfulSSHDriver):
    def run_checked_command(
        self,
        hostname: str,
        port: int,
        username: str,
        host_key: SSHHostKeyResult,
        command: list[str],
        timeout_seconds: int = 10,
    ) -> SSHCommandResult:
        return SSHCommandResult(
            exit_code=2,
            stdout="",
            stderr="df failed",
        )


def test_verify_host_key_trusts_discovered_fingerprint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeSuccessfulSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 01",
            "hostname": "remote01.example.test",
            "ssh_username": "vaultkeeper",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/verify-host-key")

    assert response.status_code == 200
    assert response.json()["fingerprint_sha256"] == "SHA256:trusted"
    assert response.json()["trusted"] is True
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["ssh_host_key_sha256"] == "SHA256:trusted"


def test_connectivity_requires_trusted_host_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeSuccessfulSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 02",
            "hostname": "remote02.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:other",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "unverified"
    assert response.json()["host_key_verified"] is False
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["status"] == "unverified"


def test_connectivity_marks_server_online_when_key_matches(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeSuccessfulSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 03",
            "hostname": "remote03.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:trusted",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["host_key_verified"] is True
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["status"] == "online"
    assert listed[0]["last_error"] is None


def test_connectivity_marks_server_offline_when_scan_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeFailingSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 04",
            "hostname": "remote04.example.test",
            "ssh_username": "vaultkeeper",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "offline"
    assert response.json()["host_key_verified"] is False
    assert response.json()["message"] == "connection timed out"


def test_inventory_collects_remote_system_snapshot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeSuccessfulSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 05",
            "hostname": "remote05.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:trusted",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/inventory")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert body["inventory"]["os"]["id"] == "debian"
    assert body["inventory"]["os"]["architecture"] == "x86_64"
    assert body["inventory"]["resources"]["cpu_count"] == 4
    assert body["inventory"]["resources"]["memory_total_kib"] == 8123456
    assert body["inventory"]["tools"]["python3"] == "/usr/bin/python3"
    assert body["inventory"]["tools"]["rsync"] is None
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["inventory"] == body["inventory"]
    assert listed[0]["last_inventory_at"] is not None


def test_inventory_requires_trusted_host_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeSuccessfulSSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 06",
            "hostname": "remote06.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:other",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/inventory")

    assert response.status_code == 409
    assert response.json()["detail"] == "SSH host key is not trusted: SHA256:trusted"
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["status"] == "unverified"


def test_inventory_reports_remote_command_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.managed_server.OpenSSHDriver",
        FakeFailingInventorySSHDriver,
    )
    create_response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote 07",
            "hostname": "remote07.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:trusted",
        },
    )
    server_uuid = create_response.json()["uuid"]

    response = client.post(f"/api/v1/managed-servers/{server_uuid}/inventory")

    assert response.status_code == 502
    assert response.json()["detail"] == "df failed"
    listed = client.get("/api/v1/managed-servers").json()
    assert listed[0]["status"] == "offline"
    assert listed[0]["last_error"] == "df failed"
