from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> DashboardService:
    return DashboardService(session)


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    return service.get_dashboard()
