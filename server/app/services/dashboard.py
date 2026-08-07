from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.repository import RepositoryRepository
from app.repositories.restore import RestoreJobRepository
from app.repositories.scheduler import BackupJobRepository
from app.repositories.snapshot import SnapshotRepository
from app.repositories.storage import StorageRepository
from app.repositories.verification import VerificationReportRepository
from app.schemas.dashboard import (
    DashboardJobMetrics,
    DashboardMetric,
    DashboardRecentRestore,
    DashboardResponse,
    DashboardRestoreMetrics,
    DashboardSnapshotMetrics,
    DashboardVerificationMetrics,
)
from app.schemas.repository import RepositoryStatus
from app.schemas.restore import RestoreStatus
from app.schemas.scheduler import BackupJobStatus
from app.schemas.snapshot import SnapshotStatus
from app.schemas.storage import StorageStatus
from app.schemas.verification import VerificationStatus


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.storage_repository = StorageRepository(session)
        self.repository_repository = RepositoryRepository(session)
        self.snapshot_repository = SnapshotRepository(session)
        self.job_repository = BackupJobRepository(session)
        self.restore_repository = RestoreJobRepository(session)
        self.verification_repository = VerificationReportRepository(session)

    def get_dashboard(self) -> DashboardResponse:
        storage = self.storage_repository.list()
        repositories = self.repository_repository.list()
        snapshots = self.snapshot_repository.list()
        jobs = self.job_repository.list()
        restores = self.restore_repository.list()
        verification_reports = self.verification_repository.list()

        return DashboardResponse(
            storage=DashboardMetric(
                total=len(storage),
                healthy=sum(
                    1 for item in storage if item.status == StorageStatus.VALID.value
                ),
                warning=sum(
                    1 for item in storage if item.status == StorageStatus.UNKNOWN.value
                ),
                failed=sum(
                    1 for item in storage if item.status == StorageStatus.INVALID.value
                ),
            ),
            repositories=DashboardMetric(
                total=len(repositories),
                healthy=sum(
                    1
                    for item in repositories
                    if item.status == RepositoryStatus.VALID.value
                ),
                warning=sum(
                    1
                    for item in repositories
                    if item.status == RepositoryStatus.UNKNOWN.value
                ),
                failed=sum(
                    1
                    for item in repositories
                    if item.status == RepositoryStatus.INVALID.value
                ),
            ),
            snapshots=DashboardSnapshotMetrics(
                total=len(snapshots),
                completed=sum(
                    1
                    for item in snapshots
                    if item.status == SnapshotStatus.COMPLETED.value
                ),
                running=sum(
                    1
                    for item in snapshots
                    if item.status == SnapshotStatus.RUNNING.value
                ),
                failed=sum(
                    1
                    for item in snapshots
                    if item.status == SnapshotStatus.FAILED.value
                ),
                total_bytes=sum(item.size_bytes or 0 for item in snapshots),
            ),
            jobs=DashboardJobMetrics(
                running=sum(
                    1 for item in jobs if item.status == BackupJobStatus.RUNNING.value
                ),
                failed=sum(
                    1 for item in jobs if item.status == BackupJobStatus.FAILED.value
                ),
                queued=sum(
                    1 for item in jobs if item.status == BackupJobStatus.QUEUED.value
                ),
                retrying=sum(
                    1 for item in jobs if item.status == BackupJobStatus.RETRYING.value
                ),
            ),
            restores=DashboardRestoreMetrics(
                total=len(restores),
                completed=sum(
                    1
                    for item in restores
                    if item.status == RestoreStatus.COMPLETED.value
                ),
                running=sum(
                    1 for item in restores if item.status == RestoreStatus.RUNNING.value
                ),
                failed=sum(
                    1 for item in restores if item.status == RestoreStatus.FAILED.value
                ),
            ),
            verification=DashboardVerificationMetrics(
                total=len(verification_reports),
                passed=sum(
                    1
                    for item in verification_reports
                    if item.status == VerificationStatus.PASSED.value
                ),
                warning=sum(
                    1
                    for item in verification_reports
                    if item.status == VerificationStatus.WARNING.value
                ),
                failed=sum(
                    1
                    for item in verification_reports
                    if item.status == VerificationStatus.FAILED.value
                ),
            ),
            recent_restores=[
                DashboardRecentRestore(
                    uuid=restore.uuid,
                    snapshot_uuid=restore.snapshot.uuid,
                    status=restore.status,
                    target_path=restore.target_path,
                    completed_at=restore.completed_at,
                    created_at=restore.created_at,
                )
                for restore in restores[:5]
            ],
        )
