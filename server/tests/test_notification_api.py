from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
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
    NotificationChannel,
    NotificationDelivery,
    Repository,
    Snapshot,
    Storage,
    VerificationReport,
)

_ = (
    NotificationChannel,
    NotificationDelivery,
    Repository,
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


def create_repository(client: TestClient, path: Path) -> tuple[str, Path]:
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Notification storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201
    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Notification repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    payload = repository_response.json()
    return str(payload["uuid"]), Path(str(payload["path"]))


def test_ntfy_channel_test_posts_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        requests.append({"url": url, **kwargs})
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)
    channel_response = client.post(
        "/api/v1/notifications/channels",
        json={
            "name": "Phone",
            "driver": "ntfy",
            "config": {
                "server_url": "https://ntfy.example.test",
                "topic": "vaultkeeper",
                "token": "secret-token",
            },
        },
    )
    assert channel_response.status_code == 201
    assert channel_response.json()["config"]["token"] == "configured"

    response = client.post(
        f"/api/v1/notifications/channels/{channel_response.json()['uuid']}/test",
        json={"title": "Test title", "message": "Test body"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert requests[0]["url"] == "https://ntfy.example.test/vaultkeeper"
    assert requests[0]["content"] == b"Test body"
    assert requests[0]["headers"]["Title"] == "Test title"
    assert requests[0]["headers"]["Authorization"] == "Bearer secret-token"


def test_webhook_channel_test_posts_json(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        requests.append({"url": url, **kwargs})
        return httpx.Response(204)

    monkeypatch.setattr(httpx, "post", fake_post)
    channel_response = client.post(
        "/api/v1/notifications/channels",
        json={
            "name": "Webhook",
            "driver": "webhook",
            "config": {"url": "https://hooks.example.test/vaultkeeper"},
        },
    )
    assert channel_response.status_code == 201

    response = client.post(
        f"/api/v1/notifications/channels/{channel_response.json()['uuid']}/test",
        json={"title": "Webhook test", "message": "Payload"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert requests[0]["url"] == "https://hooks.example.test/vaultkeeper"
    assert requests[0]["json"]["event_type"] == "notification.test"


def test_notification_channel_requires_driver_config(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notifications/channels",
        json={"name": "Broken ntfy", "driver": "ntfy", "config": {}},
    )

    assert response.status_code == 422


def test_failed_verification_sends_notification(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    requests: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        requests.append({"url": url, **kwargs})
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)
    channel_response = client.post(
        "/api/v1/notifications/channels",
        json={
            "name": "Ops phone",
            "driver": "ntfy",
            "config": {
                "server_url": "https://ntfy.example.test",
                "topic": "vaultkeeper-alerts",
            },
        },
    )
    assert channel_response.status_code == 201
    repository_root = tmp_path / "repository-root"
    repository_root.mkdir()
    repository_uuid, repository_path = create_repository(client, repository_root)
    (repository_path / "repository.json").write_text("{}", encoding="utf-8")

    response = client.post(f"/api/v1/verification/repositories/{repository_uuid}")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    deliveries_response = client.get("/api/v1/notifications/deliveries")
    assert deliveries_response.status_code == 200
    assert deliveries_response.json()[0]["event_type"] == "verification.failed"
    assert requests[0]["url"] == "https://ntfy.example.test/vaultkeeper-alerts"
