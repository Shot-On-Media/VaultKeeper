from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.verification import VerificationReportResponse
from app.services.verification import VerificationService

router = APIRouter(prefix="/verification", tags=["verification"])


def get_verification_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> VerificationService:
    return VerificationService(session)


@router.get("/reports", response_model=list[VerificationReportResponse])
def list_reports(
    service: Annotated[VerificationService, Depends(get_verification_service)],
) -> list[VerificationReportResponse]:
    return service.list_reports()


@router.post(
    "/repositories/{repository_uuid}",
    response_model=VerificationReportResponse,
)
def verify_repository(
    repository_uuid: str,
    service: Annotated[VerificationService, Depends(get_verification_service)],
) -> VerificationReportResponse:
    return service.verify_repository(repository_uuid)


@router.post(
    "/snapshots/{snapshot_uuid}",
    response_model=VerificationReportResponse,
)
def verify_snapshot(
    snapshot_uuid: str,
    service: Annotated[VerificationService, Depends(get_verification_service)],
) -> VerificationReportResponse:
    return service.verify_snapshot(snapshot_uuid)
