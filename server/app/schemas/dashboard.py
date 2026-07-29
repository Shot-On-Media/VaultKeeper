from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    total: int
    healthy: int
    warning: int
    failed: int


class DashboardSnapshotMetrics(BaseModel):
    total: int
    completed: int
    running: int
    failed: int
    total_bytes: int


class DashboardJobMetrics(BaseModel):
    running: int
    failed: int
    queued: int
    retrying: int


class DashboardRestoreMetrics(BaseModel):
    total: int
    completed: int
    running: int
    failed: int


class DashboardVerificationMetrics(BaseModel):
    total: int
    passed: int
    warning: int
    failed: int


class DashboardRecentRestore(BaseModel):
    uuid: str
    snapshot_uuid: str
    status: str
    target_path: str
    completed_at: datetime | None
    created_at: datetime


class DashboardResponse(BaseModel):
    storage: DashboardMetric
    repositories: DashboardMetric
    snapshots: DashboardSnapshotMetrics
    jobs: DashboardJobMetrics
    restores: DashboardRestoreMetrics
    verification: DashboardVerificationMetrics
    recent_restores: list[DashboardRecentRestore]
