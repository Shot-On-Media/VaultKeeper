from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_version_endpoint_returns_foundation_metadata() -> None:
    app = create_app(
        Settings(
            db_name="vaultkeeper",
            db_user="vaultkeeper",
            db_password="vaultkeeper",
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "VaultKeeper",
        "version": "0.1.0-alpha1",
        "codename": "Foundation",
        "repository_format": 1,
        "database_schema": 1,
        "protocol": 1,
    }


def test_health_endpoint_reports_dependency_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import health as health_service

    def dependency_status() -> dict[str, str]:
        return {"database": "online", "redis": "online"}

    monkeypatch.setattr(health_service, "dependency_status", dependency_status)
    app = create_app(
        Settings(
            db_name="vaultkeeper",
            db_user="vaultkeeper",
            db_password="vaultkeeper",
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    assert payload["api"] == "online"
    assert payload["database"] == "online"
    assert payload["redis"] == "online"
    assert payload["version"] == "0.1.0-alpha1"
    assert datetime.fromisoformat(payload["timestamp"])
