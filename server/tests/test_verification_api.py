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
from app.models import Repository, Snapshot, Storage, VerificationReport

_ = (Repository, Snapshot, Storage, VerificationReport)


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
            "name": "Verification storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Verification repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    payload = repository_response.json()
    return str(payload["uuid"]), Path(str(payload["path"]))


def create_filesystem_snapshot(
    client: TestClient,
    repository_uuid: str,
    source_path: Path,
) -> str:
    backup_response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(source_path),
        },
    )
    assert backup_response.status_code == 201
    return str(backup_response.json()["snapshot"]["uuid"])


def test_verify_snapshot_passes_with_checksum(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    repository_uuid, _repository_path = create_repository(client, repository_root)
    snapshot_uuid = create_filesystem_snapshot(client, repository_uuid, source_path)

    response = client.post(f"/api/v1/verification/snapshots/{snapshot_uuid}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "snapshot"
    assert payload["status"] == "passed"
    assert payload["checked_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["details"]["sha256"]


def test_verify_snapshot_fails_when_artifact_is_missing(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    repository_uuid, repository_path = create_repository(client, repository_root)
    snapshot_uuid = create_filesystem_snapshot(client, repository_uuid, source_path)
    for artifact in (repository_path / "snapshots").glob("*.zst"):
        artifact.unlink()

    response = client.post(f"/api/v1/verification/snapshots/{snapshot_uuid}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["failed_count"] == 1
    assert payload["message"] == "Snapshot artifact is missing."


def test_verify_repository_records_integrity_report(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "alpha.txt").write_text("alpha", encoding="utf-8")
    repository_uuid, _repository_path = create_repository(client, repository_root)
    snapshot_uuid = create_filesystem_snapshot(client, repository_uuid, source_path)

    response = client.post(f"/api/v1/verification/repositories/{repository_uuid}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "repository"
    assert payload["status"] == "passed"
    assert payload["snapshot_uuid"] is None
    assert payload["details"]["snapshots"][0]["snapshot_uuid"] == snapshot_uuid

    reports_response = client.get("/api/v1/verification/reports")

    assert reports_response.status_code == 200
    assert [item["uuid"] for item in reports_response.json()] == [payload["uuid"]]


def test_verify_repository_fails_when_metadata_is_tampered(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid, repository_path = create_repository(client, repository_root)
    (repository_path / "repository.json").write_text("{}", encoding="utf-8")

    response = client.post(f"/api/v1/verification/repositories/{repository_uuid}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["failed_count"] == 1
    assert payload["details"]["layout"]["metadata"]["status"] == "mismatched"
