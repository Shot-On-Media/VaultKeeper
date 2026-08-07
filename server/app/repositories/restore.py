from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.restore import RestoreJob


class RestoreJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[RestoreJob]:
        return list(
            self.session.scalars(
                select(RestoreJob).order_by(RestoreJob.created_at.desc())
            )
        )

    def get_by_uuid(self, restore_uuid: str) -> RestoreJob | None:
        return self.session.scalar(
            select(RestoreJob).where(RestoreJob.uuid == restore_uuid)
        )

    def add(self, restore_job: RestoreJob) -> RestoreJob:
        self.session.add(restore_job)
        self.session.flush()
        self.session.refresh(restore_job)
        return restore_job
