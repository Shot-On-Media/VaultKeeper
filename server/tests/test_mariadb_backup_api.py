from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.session import get_database_session
from app.drivers.snapshot.mariadb import MariaDBConnectionConfig
from app.drivers.ssh import SSHHostKeyResult, SSHStreamCommandResult
from app.main import create_app
from app.models import ManagedServer, Repository, Snapshot, Storage
from app.services.mariadb_backup import MariaDBBackupService

_ = (ManagedServer, Repository, Snapshot, Storage)


class FakeMariaDBSnapshotDriver:
    def discover_databases(self, config: MariaDBConnectionConfig) -> list[str]:
        return ["vaultkeeper", "customer"]

    def dump_database(
        self,
        config: MariaDBConnectionConfig,
        database_name: str,
        dump_path: Path,
    ) -> None:
        dump_path.write_text(f"CREATE DATABASE `{database_name}`;\n", encoding="utf-8")

    def compress_zstd(self, dump_path: Path, compressed_path: Path) -> None:
        compressed_path.write_bytes(dump_path.read_bytes())


class FakeRemoteMariaDBSSHDriver:
    def scan_host_key(self, hostname: str, port: int) -> SSHHostKeyResult:
        return SSHHostKeyResult(
            fingerprint_sha256="SHA256:trusted",
            known_hosts_entry=f"[{hostname}]:{port} ssh-ed25519 AAAA",
        )

    def stream_checked_binary_command(
        self,
        hostname: str,
        port: int,
        username: str,
        host_key: SSHHostKeyResult,
        command: list[str],
        destination_path: Path,
        timeout_seconds: int = 3600,
    ) -> SSHStreamCommandResult:
        assert command[:9] == [
            "vaultkeeper",
            "mariadb-snapshot",
            "--host",
            "127.0.0.1",
            "--port",
            "3306",
            "--user",
            "vaultkeeper",
            "--password",
        ]
        assert command[10:] == [
            "--database",
            "customer",
        ]
        destination_path.write_bytes(b"compressed remote sql")
        return SSHStreamCommandResult(
            exit_code=0,
            stderr='{"source_bytes": 128}',
        )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
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

    original_init = MariaDBBackupService.__init__

    def patched_init(self: MariaDBBackupService, session: Session) -> None:
        original_init(self, session)
        self.driver = FakeMariaDBSnapshotDriver()
        self.ssh_driver = FakeRemoteMariaDBSSHDriver()

    monkeypatch.setattr(MariaDBBackupService, "__init__", patched_init)
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


def create_repository(client: TestClient, path: Path) -> str:
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "MariaDB backup storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "MariaDB backup repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    return str(repository_response.json()["uuid"])


def create_managed_server(client: TestClient) -> str:
    response = client.post(
        "/api/v1/managed-servers",
        json={
            "name": "Remote db",
            "hostname": "remote-db.example.test",
            "ssh_username": "vaultkeeper",
            "ssh_host_key_sha256": "SHA256:trusted",
        },
    )
    assert response.status_code == 201
    return str(response.json()["uuid"])


def test_mariadb_database_discovery(client: TestClient) -> None:
    response = client.get("/api/v1/mariadb-backups/databases")

    assert response.status_code == 200
    assert response.json() == {"databases": ["vaultkeeper", "customer"]}


def test_mariadb_backup_creates_completed_snapshot(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid = create_repository(client, repository_root)

    response = client.post(
        "/api/v1/mariadb-backups",
        json={
            "repository_uuid": repository_uuid,
            "database_name": "vaultkeeper",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    artifact_path = Path(payload["artifact_path"])
    assert artifact_path.is_file()
    assert artifact_path.suffix == ".zst"
    assert payload["database_name"] == "vaultkeeper"
    assert payload["dump_bytes"] > 0
    assert payload["compressed_bytes"] > 0
    assert payload["snapshot"]["engine"] == "mariadb"
    assert payload["snapshot"]["status"] == "completed"
    assert payload["snapshot"]["manifest"]["artifact"] == artifact_path.name
    assert payload["snapshot"]["manifest"]["sha256"]


def test_remote_mariadb_backup_creates_completed_snapshot(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid = create_repository(client, repository_root)
    managed_server_uuid = create_managed_server(client)

    response = client.post(
        "/api/v1/mariadb-backups",
        json={
            "repository_uuid": repository_uuid,
            "managed_server_uuid": managed_server_uuid,
            "database_name": "customer",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    artifact_path = Path(payload["artifact_path"])
    assert artifact_path.read_bytes() == b"compressed remote sql"
    assert payload["database_name"] == "customer"
    assert payload["dump_bytes"] == 128
    assert payload["compressed_bytes"] == len(b"compressed remote sql")
    assert payload["snapshot"]["source"] == "Remote db:customer"
    assert payload["snapshot"]["manifest"]["managed_server_uuid"] == managed_server_uuid
    assert payload["snapshot"]["manifest"]["remote_hostname"] == (
        "remote-db.example.test"
    )
