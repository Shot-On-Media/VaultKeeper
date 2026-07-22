from __future__ import annotations

import json
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
from app.models import Repository, Storage
from app.services.repository import REPOSITORY_DIRECTORIES

_ = (Repository, Storage)


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


def create_storage(client: TestClient, path: Path) -> str:
    response = client.post(
        "/api/v1/storage",
        json={
            "name": "Local storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )

    assert response.status_code == 201
    return str(response.json()["uuid"])


def test_repository_crud_creates_layout(
    client: TestClient,
    tmp_path: Path,
) -> None:
    storage_uuid = create_storage(client, tmp_path)
    create_response = client.post(
        "/api/v1/repositories",
        json={"name": "Primary repository", "storage_uuid": storage_uuid},
    )

    assert create_response.status_code == 201
    created = create_response.json()
    repository_path = tmp_path / created["uuid"]
    assert created["status"] == "valid"
    assert created["path"] == str(repository_path)
    assert repository_path.is_dir()
    assert (repository_path / "repository.json").is_file()
    for directory_name in REPOSITORY_DIRECTORIES:
        assert (repository_path / directory_name).is_dir()

    metadata = json.loads((repository_path / "repository.json").read_text())
    assert metadata["uuid"] == created["uuid"]
    assert metadata["storage_uuid"] == storage_uuid

    validate_response = client.post(f"/api/v1/repositories/{created['uuid']}/validate")

    assert validate_response.status_code == 200
    assert validate_response.json()["status"] == "valid"

    update_response = client.put(
        f"/api/v1/repositories/{created['uuid']}",
        json={"name": "Renamed repository"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed repository"

    list_response = client.get("/api/v1/repositories")

    assert list_response.status_code == 200
    assert [item["uuid"] for item in list_response.json()] == [created["uuid"]]

    delete_response = client.delete(f"/api/v1/repositories/{created['uuid']}")

    assert delete_response.status_code == 204
    assert client.get("/api/v1/repositories").json() == []


def test_repository_requires_existing_storage(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Missing storage repository",
            "storage_uuid": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 404


def test_repository_with_snapshots_cannot_be_deleted(
    client: TestClient,
    tmp_path: Path,
) -> None:
    storage_uuid = create_storage(client, tmp_path)
    repository_response = client.post(
        "/api/v1/repositories",
        json={"name": "Primary repository", "storage_uuid": storage_uuid},
    )
    repository_uuid = repository_response.json()["uuid"]
    snapshot_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "test_engine",
            "source": "/srv/data",
        },
    )

    assert snapshot_response.status_code == 201
    response = client.delete(f"/api/v1/repositories/{repository_uuid}")

    assert response.status_code == 409
