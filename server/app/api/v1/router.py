from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.filesystem_backups import router as filesystem_backups_router
from app.api.v1.mariadb_backups import router as mariadb_backups_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.restores import router as restores_router
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.storage import router as storage_router
from app.api.v1.system import router as system_router
from app.api.v1.verification import router as verification_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
router.include_router(dashboard_router)
router.include_router(storage_router)
router.include_router(repositories_router)
router.include_router(snapshots_router)
router.include_router(filesystem_backups_router)
router.include_router(mariadb_backups_router)
router.include_router(scheduler_router)
router.include_router(restores_router)
router.include_router(verification_router)
