from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.repositories import router as repositories_router
from app.api.v1.snapshots import router as snapshots_router
from app.api.v1.storage import router as storage_router
from app.api.v1.system import router as system_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
router.include_router(storage_router)
router.include_router(repositories_router)
router.include_router(snapshots_router)
