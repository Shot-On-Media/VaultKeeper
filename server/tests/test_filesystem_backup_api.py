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
from app.models import Repository, Snapshot, Storage

_ = (Repository, Snapshot, Storage)


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


def create_repository(client: TestClient, path: Path) -> str:
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Filesystem backup storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Filesystem backup repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    return str(repository_response.json()["uuid"])


def test_filesystem_backup_creates_completed_snapshot(
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
    repository_uuid = create_repository(client, repository_root)

    response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(source_path),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    artifact_path = Path(payload["artifact_path"])
    assert artifact_path.is_file()
    assert artifact_path.suffix == ".zst"
    assert payload["file_count"] == 2
    assert payload["source_bytes"] == 9
    assert payload["compressed_bytes"] > 0
    assert payload["snapshot"]["engine"] == "filesystem"
    assert payload["snapshot"]["status"] == "completed"
    assert payload["snapshot"]["manifest"]["artifact"] == artifact_path.name
    assert payload["snapshot"]["manifest"]["sha256"]


def test_filesystem_backup_requires_existing_source(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid = create_repository(client, repository_root)

    response = client.post(
        "/api/v1/filesystem-backups",
        json={
            "repository_uuid": repository_uuid,
            "source_path": str(tmp_path / "missing"),
        },
    )

    assert response.status_code == 422
