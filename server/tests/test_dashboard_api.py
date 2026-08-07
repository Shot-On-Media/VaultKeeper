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
from app.main import create_app
from app.models import (
    BackupJob,
    BackupPolicy,
    Repository,
    RestoreJob,
    Snapshot,
    Storage,
    VerificationReport,
)

_ = (
    BackupJob,
    BackupPolicy,
    Repository,
    RestoreJob,
    Snapshot,
    Storage,
    VerificationReport,
)


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


def create_repository(client: TestClient, path: Path) -> tuple[str, str, Path]:
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Dashboard storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Dashboard repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    payload = repository_response.json()
    return (
        str(storage_response.json()["uuid"]),
        str(payload["uuid"]),
        Path(str(payload["path"])),
    )


def test_dashboard_returns_empty_operational_summary(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"] == {
        "total": 0,
        "healthy": 0,
        "warning": 0,
        "failed": 0,
    }
    assert payload["repositories"]["total"] == 0
    assert payload["snapshots"]["total"] == 0
    assert payload["jobs"]["running"] == 0
    assert payload["restores"]["total"] == 0
    assert payload["verification"]["total"] == 0
    assert payload["recent_restores"] == []


def test_dashboard_summarizes_operational_health(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    restore_target = tmp_path / "restore-target"
    storage_uuid, repository_uuid, _repository_path = create_repository(
        client,
        repository_root,
    )
    storage_validation_response = client.post(
        f"/api/v1/storage/{storage_uuid}/validate"
    )
    assert storage_validation_response.status_code == 200

    backup_response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(source_path),
        },
    )
    assert backup_response.status_code == 201
    snapshot_uuid = str(backup_response.json()["snapshot"]["uuid"])

    restore_response = client.post(
        "/api/v1/restores",
        json={
            "snapshot_uuid": snapshot_uuid,
            "target_path": str(restore_target),
        },
    )
    assert restore_response.status_code == 201

    verification_response = client.post(
        f"/api/v1/verification/repositories/{repository_uuid}"
    )
    assert verification_response.status_code == 200

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"]["healthy"] == 1
    assert payload["repositories"]["healthy"] == 1
    assert payload["snapshots"]["completed"] == 1
    assert payload["snapshots"]["total_bytes"] > 0
    assert payload["restores"]["completed"] == 1
    assert payload["verification"]["passed"] == 1
    assert payload["recent_restores"][0]["snapshot_uuid"] == snapshot_uuid
