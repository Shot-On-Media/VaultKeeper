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
from app.models import APIKey, AuditLog

_ = (APIKey, AuditLog)


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
            security_enabled=True,
            security_secret="test-security-secret",
            admin_username="admin",
            admin_password="correct-password",
        )
    )
    app.dependency_overrides[get_database_session] = override_database_session
    app.state.audit_session_factory = session_factory

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_protected_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401


def test_admin_login_returns_bearer_token(client: TestClient) -> None:
    token = login(client)

    response = client.get(
        "/api/v1/security/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"actor": "admin", "auth_type": "password"}


def test_api_key_secret_is_created_once_and_can_authenticate(
    client: TestClient,
) -> None:
    token = login(client)
    create_response = client.post(
        "/api/v1/security/api-keys",
        json={"name": "Automation"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    secret = str(create_response.json()["secret"])
    assert secret.startswith("vk_")

    list_response = client.get(
        "/api/v1/security/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    assert "secret" not in list_response.json()[0]
    assert list_response.json()[0]["key_prefix"] == secret[:12]

    dashboard_response = client.get(
        "/api/v1/dashboard",
        headers={"X-API-Key": secret},
    )

    assert dashboard_response.status_code == 200


def test_audit_log_records_mutating_authenticated_requests(
    client: TestClient,
) -> None:
    token = login(client)

    create_response = client.post(
        "/api/v1/security/api-keys",
        json={"name": "Audit key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    audit_response = client.get(
        "/api/v1/security/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["actor"] == "admin"
    assert audit_response.json()[0]["method"] == "POST"
    assert audit_response.json()[0]["path"] == "/api/v1/security/api-keys"
