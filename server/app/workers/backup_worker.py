from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.scheduler import BackupJobRepository
from app.schemas.filesystem_backup import FilesystemBackupCreate
from app.schemas.mariadb_backup import MariaDBBackupCreate
from app.schemas.scheduler import BackupEngine, BackupJobResponse, BackupJobStatus
from app.services.filesystem_backup import FilesystemBackupService
from app.services.mariadb_backup import MariaDBBackupService
from app.services.queue import BackupQueue


class BackupWorker:
    def __init__(self, session: Session, queue: BackupQueue | None = None) -> None:
        self.job_repository = BackupJobRepository(session)
        self.queue = queue or BackupQueue()
        self.session = session

    def process_next(self) -> BackupJobResponse | None:
        job_uuid = self.queue.dequeue()
        job = self.job_repository.get_by_uuid(job_uuid) if job_uuid else None
        if job is None:
            job = self.job_repository.next_queued()
        if job is None:
            return None

        job.status = BackupJobStatus.RUNNING.value
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        self.session.commit()

        try:
            if job.policy.engine == BackupEngine.FILESYSTEM.value:
                result = FilesystemBackupService(self.session).run_backup(
                    FilesystemBackupCreate(
                        repository_uuid=job.policy.repository.uuid,
                        source_path=job.policy.source,
                    )
                )
            elif job.policy.engine == BackupEngine.MARIADB.value:
                result = MariaDBBackupService(self.session).run_backup(
                    MariaDBBackupCreate(
                        repository_uuid=job.policy.repository.uuid,
                        database_name=job.policy.source,
                    )
                )
            else:
                raise RuntimeError(f"Unsupported backup engine: {job.policy.engine}")
        except (HTTPException, RuntimeError) as exc:
            job.error_message = str(
                exc.detail if isinstance(exc, HTTPException) else exc
            )
            job.completed_at = datetime.now(UTC)
            if job.attempts < job.max_attempts:
                job.status = BackupJobStatus.RETRYING.value
                self.session.commit()
                self.queue.enqueue(job.uuid)
            else:
                job.status = BackupJobStatus.FAILED.value
                self.session.commit()
            self.session.refresh(job)
            return self._to_response(job)

        job.status = BackupJobStatus.COMPLETED.value
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        job.snapshot_uuid = result.snapshot.uuid
        self.session.commit()
        self.session.refresh(job)
        return self._to_response(job)

    def _to_response(self, job: object) -> BackupJobResponse:
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
