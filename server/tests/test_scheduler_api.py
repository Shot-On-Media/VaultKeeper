from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.scheduler import get_backup_worker, get_scheduler_service
from app.core.config import Settings
from app.database.base import Base
from app.database.session import get_database_session
from app.main import create_app
from app.models import BackupJob, BackupPolicy, Repository, Snapshot, Storage
from app.services.scheduler import SchedulerService
from app.workers.backup_worker import BackupWorker

_ = (BackupJob, BackupPolicy, Repository, Snapshot, Storage)


class FakeBackupQueue:
    def __init__(self) -> None:
        self.items: list[str] = []

    def enqueue(self, job_uuid: str) -> None:
        self.items.append(job_uuid)

    def dequeue(self) -> str | None:
        return self.items.pop(0) if self.items else None


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
    queue = FakeBackupQueue()

    def override_database_session() -> Generator[Session]:
        with session_factory() as session:
            yield session

    def override_scheduler_service() -> Generator[SchedulerService]:
        with session_factory() as session:
            yield SchedulerService(session, queue=queue)  # type: ignore[arg-type]

    def override_backup_worker() -> Generator[BackupWorker]:
        with session_factory() as session:
            yield BackupWorker(session, queue=queue)  # type: ignore[arg-type]

    app = create_app(
        Settings(
            db_name="vaultkeeper",
            db_user="vaultkeeper",
            db_password="vaultkeeper",
            scheduler_enabled=False,
        )
    )
    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_scheduler_service] = override_scheduler_service
    app.dependency_overrides[get_backup_worker] = override_backup_worker

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_repository(client: TestClient, path: Path) -> str:
    path.mkdir()
    storage_response = client.post(
        "/api/v1/storage",
        json={
            "name": "Scheduler storage",
            "driver": "local_filesystem",
            "config": {"path": str(path)},
        },
    )
    assert storage_response.status_code == 201

    repository_response = client.post(
        "/api/v1/repositories",
        json={
            "name": "Scheduler repository",
            "storage_uuid": storage_response.json()["uuid"],
        },
    )
    assert repository_response.status_code == 201
    return str(repository_response.json()["uuid"])


def create_policy(
    client: TestClient,
    repository_uuid: str,
    source_path: Path,
    next_run_at: datetime,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/scheduler/policies",
        json={
            "name": "Filesystem schedule",
            "repository_uuid": repository_uuid,
            "engine": "filesystem",
            "source": str(source_path),
            "interval_minutes": 15,
            "enabled": True,
            "next_run_at": next_run_at.isoformat(),
            "max_retries": 1,
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def test_scheduler_policy_crud_and_due_enqueue(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_uuid = create_repository(client, tmp_path / "repo-root")
    source_path = tmp_path / "source"
    source_path.mkdir()
    policy = create_policy(
        client,
        repository_uuid,
        source_path,
        datetime.now(UTC) - timedelta(minutes=1),
    )

    list_response = client.get("/api/v1/scheduler/policies")
    assert list_response.status_code == 200
    assert [item["uuid"] for item in list_response.json()] == [policy["uuid"]]

    tick_response = client.post("/api/v1/scheduler/tick")
    assert tick_response.status_code == 200
    assert len(tick_response.json()["enqueued_jobs"]) == 1

    jobs_response = client.get("/api/v1/scheduler/jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.json()[0]["status"] == "queued"

    update_response = client.put(
        f"/api/v1/scheduler/policies/{policy['uuid']}",
        json={"enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False


def test_worker_processes_filesystem_policy(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_uuid = create_repository(client, tmp_path / "repo-root")
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "data.txt").write_text("payload", encoding="utf-8")
    policy = create_policy(client, repository_uuid, source_path, datetime.now(UTC))

    enqueue_response = client.post(
        f"/api/v1/scheduler/policies/{policy['uuid']}/enqueue"
    )
    assert enqueue_response.status_code == 200

    worker_response = client.post("/api/v1/scheduler/work")
    assert worker_response.status_code == 200
    job = worker_response.json()["job"]
    assert job["status"] == "completed"
    assert job["attempts"] == 1
    assert job["snapshot_uuid"] is not None


def test_worker_retries_failed_policy(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_uuid = create_repository(client, tmp_path / "repo-root")
    missing_source_path = tmp_path / "missing"
    policy = create_policy(
        client,
        repository_uuid,
        missing_source_path,
        datetime.now(UTC),
    )

    enqueue_response = client.post(
        f"/api/v1/scheduler/policies/{policy['uuid']}/enqueue"
    )
    assert enqueue_response.status_code == 200

    first_run = client.post("/api/v1/scheduler/work").json()["job"]
    second_run = client.post("/api/v1/scheduler/work").json()["job"]

    assert first_run["status"] == "retrying"
    assert second_run["status"] == "failed"
    assert second_run["attempts"] == 2
