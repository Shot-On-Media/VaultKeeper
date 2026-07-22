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
            "name": "Snapshot storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Snapshot repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    return str(repository_response.json()["uuid"])


def test_snapshot_lifecycle_and_history(client: TestClient, tmp_path: Path) -> None:
    repository_uuid = create_repository(client, tmp_path)
    register_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "test_engine",
            "source": "/srv/data",
            "manifest": {"files": 2},
        },
    )

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["repository_uuid"] == repository_uuid
    assert registered["status"] == "pending"

    start_response = client.post(f"/api/v1/snapshots/{registered['uuid']}/start")

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert start_response.json()["started_at"] is not None

    complete_response = client.post(
        f"/api/v1/snapshots/{registered['uuid']}/complete",
        json={"size_bytes": 2048, "manifest": {"archive": "snapshot.tar.zst"}},
    )

    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "completed"
    assert completed["size_bytes"] == 2048
    assert completed["completed_at"] is not None

    history_response = client.get(
        "/api/v1/snapshots",
        params={"repository_uuid": repository_uuid},
    )

    assert history_response.status_code == 200
    assert [item["uuid"] for item in history_response.json()] == [registered["uuid"]]


def test_snapshot_lifecycle_rejects_invalid_transition(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_uuid = create_repository(client, tmp_path)
    register_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "test_engine",
            "source": "/srv/data",
        },
    )
    snapshot_uuid = register_response.json()["uuid"]

    response = client.post(
        f"/api/v1/snapshots/{snapshot_uuid}/complete",
        json={"size_bytes": 2048, "manifest": {}},
    )

    assert response.status_code == 409


def test_snapshot_can_fail_from_pending(client: TestClient, tmp_path: Path) -> None:
    repository_uuid = create_repository(client, tmp_path)
    register_response = client.post(
        "/api/v1/snapshots",
        json={
            "repository_uuid": repository_uuid,
            "engine": "test_engine",
            "source": "/srv/data",
        },
    )
    snapshot_uuid = register_response.json()["uuid"]

    response = client.post(
        f"/api/v1/snapshots/{snapshot_uuid}/fail",
        json={"failure_message": "source unavailable"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["failure_message"] == "source unavailable"
