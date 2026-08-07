from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.scheduler import (
    BackupJobResponse,
    BackupPolicyCreate,
    BackupPolicyResponse,
    BackupPolicyUpdate,
    SchedulerRunResponse,
    WorkerRunResponse,
)
from app.services.scheduler import SchedulerService
from app.workers.backup_worker import BackupWorker

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def get_scheduler_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> SchedulerService:
    return SchedulerService(session)


def get_backup_worker(
    session: Annotated[Session, Depends(get_database_session)],
) -> BackupWorker:
    return BackupWorker(session)


@router.get("/policies", response_model=list[BackupPolicyResponse])
def list_policies(
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> list[BackupPolicyResponse]:
    return service.list_policies()


@router.post(
    "/policies",
    response_model=BackupPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_policy(
    payload: BackupPolicyCreate,
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> BackupPolicyResponse:
    return service.create_policy(payload)


@router.put("/policies/{policy_uuid}", response_model=BackupPolicyResponse)
def update_policy(
    policy_uuid: str,
    payload: BackupPolicyUpdate,
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> BackupPolicyResponse:
    return service.update_policy(policy_uuid, payload)


@router.delete("/policies/{policy_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_uuid: str,
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> Response:
    service.delete_policy(policy_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/policies/{policy_uuid}/enqueue", response_model=BackupJobResponse)
def enqueue_policy(
    policy_uuid: str,
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> BackupJobResponse:
    return service.enqueue_policy(policy_uuid)


@router.get("/jobs", response_model=list[BackupJobResponse])
def list_jobs(
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> list[BackupJobResponse]:
    return service.list_jobs()


@router.post("/tick", response_model=SchedulerRunResponse)
def enqueue_due_policies(
    service: Annotated[SchedulerService, Depends(get_scheduler_service)],
) -> SchedulerRunResponse:
    return SchedulerRunResponse(enqueued_jobs=service.enqueue_due_policies())


@router.post("/work", response_model=WorkerRunResponse)
def process_next_job(
    worker: Annotated[BackupWorker, Depends(get_backup_worker)],
) -> WorkerRunResponse:
    return WorkerRunResponse(job=worker.process_next())
