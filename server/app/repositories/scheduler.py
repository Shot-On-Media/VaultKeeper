from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduler import BackupJob, BackupPolicy
from app.schemas.scheduler import BackupJobStatus


class BackupPolicyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[BackupPolicy]:
        return list(
            self.session.scalars(select(BackupPolicy).order_by(BackupPolicy.name))
        )

    def list_due(self, now: datetime) -> list[BackupPolicy]:
        return list(
            self.session.scalars(
                select(BackupPolicy)
                .where(BackupPolicy.enabled.is_(True))
                .where(BackupPolicy.next_run_at <= now)
                .order_by(BackupPolicy.next_run_at)
            )
        )

    def get_by_uuid(self, policy_uuid: str) -> BackupPolicy | None:
        return self.session.scalar(
            select(BackupPolicy).where(BackupPolicy.uuid == policy_uuid)
        )

    def get_by_name(self, name: str) -> BackupPolicy | None:
        return self.session.scalar(
            select(BackupPolicy).where(BackupPolicy.name == name)
        )

    def add(self, policy: BackupPolicy) -> BackupPolicy:
        self.session.add(policy)
        self.session.flush()
        self.session.refresh(policy)
        return policy

    def delete(self, policy: BackupPolicy) -> None:
        self.session.delete(policy)
        self.session.flush()


class BackupJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[BackupJob]:
        return list(
            self.session.scalars(select(BackupJob).order_by(BackupJob.queued_at.desc()))
        )

    def get_by_uuid(self, job_uuid: str) -> BackupJob | None:
        return self.session.scalar(select(BackupJob).where(BackupJob.uuid == job_uuid))

    def next_queued(self) -> BackupJob | None:
        return self.session.scalar(
            select(BackupJob)
            .where(
                BackupJob.status.in_([BackupJobStatus.QUEUED, BackupJobStatus.RETRYING])
            )
            .order_by(BackupJob.queued_at)
            .limit(1)
        )

    def add(self, job: BackupJob) -> BackupJob:
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job
