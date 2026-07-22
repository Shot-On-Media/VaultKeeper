from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.session import get_database_session
from app.main import create_app
from app.models import Storage

_ = Storage


@pytest.fixture
def test_engine() -> Generator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_engine: Engine) -> Generator[TestClient]:
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
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


def test_storage_crud_and_validation(
    client: TestClient,
    tmp_path: Path,
) -> None:
    create_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Local backups",
            "driver": "local_filesystem",
            "config": {"path": str(tmp_path)},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Local backups"
    assert created["driver"] == "local_filesystem"
    assert created["status"] == "unknown"

    list_response = client.get("/api/v1/storage")

    assert list_response.status_code == 200
    assert [item["uuid"] for item in list_response.json()] == [created["uuid"]]

    validate_response = client.post(f"/api/v1/storage/{created['uuid']}/validate")

    assert validate_response.status_code == 200
    assert validate_response.json()["status"] == "valid"

    update_response = client.put(
        f"/api/v1/storage/{created['uuid']}",
        json={
            "name": "Primary local backups",
            "config": {"path": str(tmp_path)},
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Primary local backups"

    delete_response = client.delete(f"/api/v1/storage/{created['uuid']}")

    assert delete_response.status_code == 204
    assert client.get("/api/v1/storage").json() == []


def test_storage_requires_absolute_local_path(client: TestClient) -> None:
    response = client.post(
        "/api/v1/storage",
        json={
            "name": "Relative storage",
            "driver": "local_filesystem",
            "config": {"path": "relative/path"},
        },
    )

    assert response.status_code == 422


def test_storage_names_must_be_unique(
    client: TestClient,
    tmp_path: Path,
) -> None:
    payload = {
        "name": "Local backups",
        "driver": "local_filesystem",
        "config": {"path": str(tmp_path)},
    }

    assert client.post("/api/v1/storage", json=payload).status_code == 201
    response = client.post("/api/v1/storage", json=payload)

    assert response.status_code == 409
