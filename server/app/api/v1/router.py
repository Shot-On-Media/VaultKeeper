from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_principal
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.filesystem_backups import router as filesystem_backups_router
from app.api.v1.managed_servers import router as managed_servers_router
from app.api.v1.mariadb_backups import router as mariadb_backups_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.restores import router as restores_router
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1.security import router as security_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.storage import router as storage_router
from app.api.v1.system import router as system_router
from app.api.v1.verification import router as verification_router

router = APIRouter(prefix="/api/v1")
protected_router = APIRouter(dependencies=[Depends(require_principal)])
router.include_router(system_router)
router.include_router(auth_router)
protected_router.include_router(dashboard_router)
protected_router.include_router(notifications_router)
protected_router.include_router(storage_router)
protected_router.include_router(repositories_router)
protected_router.include_router(snapshots_router)
protected_router.include_router(filesystem_backups_router)
protected_router.include_router(mariadb_backups_router)
protected_router.include_router(managed_servers_router)
protected_router.include_router(scheduler_router)
protected_router.include_router(restores_router)
protected_router.include_router(verification_router)
protected_router.include_router(security_router)
router.include_router(protected_router)
