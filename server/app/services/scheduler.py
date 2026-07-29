from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.scheduler import BackupJob, BackupPolicy
from app.repositories.repository import RepositoryRepository
from app.repositories.scheduler import BackupJobRepository, BackupPolicyRepository
from app.schemas.scheduler import (
    BackupJobResponse,
    BackupJobStatus,
    BackupPolicyCreate,
    BackupPolicyResponse,
    BackupPolicyUpdate,
)
from app.services.queue import BackupQueue


class SchedulerService:
    def __init__(self, session: Session, queue: BackupQueue | None = None) -> None:
        self.job_repository = BackupJobRepository(session)
        self.policy_repository = BackupPolicyRepository(session)
        self.repository_repository = RepositoryRepository(session)
        self.queue = queue or BackupQueue()
        self.session = session

    def list_policies(self) -> list[BackupPolicyResponse]:
        return [
            self._policy_to_response(policy) for policy in self.policy_repository.list()
        ]

    def create_policy(self, payload: BackupPolicyCreate) -> BackupPolicyResponse:
        if self.policy_repository.get_by_name(payload.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Backup policy name already exists.",
            )
        repository = self.repository_repository.get_by_uuid(payload.repository_uuid)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found.",
            )

        policy = BackupPolicy(
            repository_id=repository.id,
            name=payload.name,
            engine=payload.engine.value,
            source=payload.source,
            interval_minutes=payload.interval_minutes,
            enabled=payload.enabled,
            next_run_at=payload.next_run_at,
            max_retries=payload.max_retries,
        )
        self.policy_repository.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return self._policy_to_response(policy)

    def update_policy(
        self,
        policy_uuid: str,
        payload: BackupPolicyUpdate,
    ) -> BackupPolicyResponse:
        policy = self._get_policy(policy_uuid)
        if payload.name is not None and payload.name != policy.name:
            if self.policy_repository.get_by_name(payload.name) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Backup policy name already exists.",
                )
            policy.name = payload.name
        if payload.source is not None:
            policy.source = payload.source
        if payload.interval_minutes is not None:
            policy.interval_minutes = payload.interval_minutes
        if payload.enabled is not None:
            policy.enabled = payload.enabled
        if payload.next_run_at is not None:
            policy.next_run_at = payload.next_run_at
        if payload.max_retries is not None:
            policy.max_retries = payload.max_retries

        self.session.commit()
        self.session.refresh(policy)
        return self._policy_to_response(policy)

    def delete_policy(self, policy_uuid: str) -> None:
        policy = self._get_policy(policy_uuid)
        self.policy_repository.delete(policy)
        self.session.commit()

    def list_jobs(self) -> list[BackupJobResponse]:
        return [self._job_to_response(job) for job in self.job_repository.list()]

    def enqueue_due_policies(
        self,
        now: datetime | None = None,
    ) -> list[BackupJobResponse]:
        resolved_now = now or datetime.now(UTC)
        enqueued_jobs: list[BackupJobResponse] = []
        for policy in self.policy_repository.list_due(resolved_now):
            job = BackupJob(
                policy_id=policy.id,
                status=BackupJobStatus.QUEUED.value,
                attempts=0,
                max_attempts=policy.max_retries + 1,
                queued_at=resolved_now,
            )
            self.job_repository.add(job)
            policy.next_run_at = resolved_now + timedelta(
                minutes=policy.interval_minutes
            )
            self.session.flush()
            self.queue.enqueue(job.uuid)
            enqueued_jobs.append(self._job_to_response(job))

        self.session.commit()
        return enqueued_jobs

    def enqueue_policy(self, policy_uuid: str) -> BackupJobResponse:
        policy = self._get_policy(policy_uuid)
        queued_at = datetime.now(UTC)
        job = BackupJob(
            policy_id=policy.id,
            status=BackupJobStatus.QUEUED.value,
            attempts=0,
            max_attempts=policy.max_retries + 1,
            queued_at=queued_at,
        )
        self.job_repository.add(job)
        self.session.commit()
        self.session.refresh(job)
        self.queue.enqueue(job.uuid)
        return self._job_to_response(job)

    def _get_policy(self, policy_uuid: str) -> BackupPolicy:
        policy = self.policy_repository.get_by_uuid(policy_uuid)
        if policy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Backup policy not found.",
            )
        return policy

    def _policy_to_response(self, policy: BackupPolicy) -> BackupPolicyResponse:
        return BackupPolicyResponse(
            uuid=policy.uuid,
            repository_uuid=policy.repository.uuid,
            name=policy.name,
            engine=policy.engine,
            source=policy.source,
            interval_minutes=policy.interval_minutes,
            enabled=policy.enabled,
            next_run_at=policy.next_run_at,
            max_retries=policy.max_retries,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    def _job_to_response(self, job: BackupJob) -> BackupJobResponse:
        return BackupJobResponse(
            uuid=job.uuid,
            policy_uuid=job.policy.uuid,
            status=job.status,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            queued_at=job.queued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            snapshot_uuid=job.snapshot_uuid,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
