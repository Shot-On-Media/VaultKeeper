from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
import zstandard
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.session import get_database_session
from app.main import create_app
from app.models import Repository, RestoreJob, Snapshot, Storage

_ = (Repository, RestoreJob, Snapshot, Storage)


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


def create_repository(client: TestClient, path: Path) -> tuple[str, Path]:
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Restore storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Restore repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    payload = repository_response.json()
    return str(payload["uuid"]), Path(str(payload["path"]))


def test_restore_filesystem_snapshot(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    nested_path = source_path / "nested"
    nested_path.mkdir()
    (nested_path / "beta.txt").write_text("beta", encoding="utf-8")
    target_path = tmp_path / "restore-target"
    repository_uuid, _repository_path = create_repository(client, repository_root)
    backup_response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(source_path),
        },
    )
    assert backup_response.status_code == 201
    snapshot_uuid = str(backup_response.json()["snapshot"]["uuid"])

    response = client.post(
        "/api/v1/restores",
        json={
            "snapshot_uuid": snapshot_uuid,
            "target_path": str(target_path),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["snapshot_uuid"] == snapshot_uuid
    assert payload["status"] == "completed"
    assert payload["progress_percent"] == 100
    assert (
        payload["verification_message"] == "Filesystem snapshot restored with 2 files."
    )
    assert (target_path / source_path.name / "alpha.txt").read_text(
        encoding="utf-8"
    ) == "alpha"
    assert (target_path / source_path.name / "nested" / "beta.txt").read_text(
        encoding="utf-8"
    ) == "beta"


def test_restore_stages_mariadb_snapshot(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid, repository_path = create_repository(client, repository_root)
    snapshot_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "mariadb",
            "source": "vaultkeeper",
            "manifest": {},
        },
    )
    assert snapshot_response.status_code == 201
    snapshot_uuid = str(snapshot_response.json()["uuid"])
    start_response = client.post(f"/api/v1/snapshots/{snapshot_uuid}/start")
    assert start_response.status_code == 200
    artifact_path = repository_path / "snapshots" / f"{snapshot_uuid}.sql.zst"
    compressor = zstandard.ZstdCompressor(level=3)
    with artifact_path.open("wb") as artifact_file:
        artifact_file.write(compressor.compress(b"CREATE TABLE restore_check(id INT);"))
    complete_response = client.post(
        f"/api/v1/snapshots/{snapshot_uuid}/complete",
        json={
            "size_bytes": artifact_path.stat().st_size,
            "manifest": {
                "artifact": artifact_path.name,
                "compression": "zstd",
                "database": "vaultkeeper",
                "format": "sql",
            },
        },
    )
    assert complete_response.status_code == 200
    target_path = tmp_path / "sql-restore-target"

    response = client.post(
        "/api/v1/restores",
        json={
            "snapshot_uuid": snapshot_uuid,
            "target_path": str(target_path),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    staged_path = target_path / f"vaultkeeper-{snapshot_uuid}.sql"
    assert (
        staged_path.read_text(encoding="utf-8") == "CREATE TABLE restore_check(id INT);"
    )
    assert payload["verification_message"] == f"MariaDB dump staged at {staged_path}."


def test_restore_rejects_incomplete_snapshot(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid, _repository_path = create_repository(client, repository_root)
    snapshot_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "filesystem",
            "source": "/srv/data",
            "manifest": {},
        },
    )
    snapshot_uuid = str(snapshot_response.json()["uuid"])

    response = client.post(
        "/api/v1/restores",
        json={
            "snapshot_uuid": snapshot_uuid,
            "target_path": str(tmp_path / "target"),
        },
    )

    assert response.status_code == 409


def test_list_restores_returns_history(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    repository_uuid, _repository_path = create_repository(client, repository_root)
    backup_response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(source_path),
        },
    )
    snapshot_uuid = str(backup_response.json()["snapshot"]["uuid"])
    restore_response = client.post(
        "/api/v1/restores",
        json={
            "snapshot_uuid": snapshot_uuid,
            "target_path": str(tmp_path / "target"),
        },
    )
    restore_uuid = str(restore_response.json()["uuid"])

    response = client.get("/api/v1/restores")

    assert response.status_code == 200
    assert [item["uuid"] for item in response.json()] == [restore_uuid]
