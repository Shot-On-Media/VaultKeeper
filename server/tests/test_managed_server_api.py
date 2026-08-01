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
