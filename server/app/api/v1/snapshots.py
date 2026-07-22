from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_database_session
from app.schemas.snapshot import (
    SnapshotComplete,
    SnapshotCreate,
    SnapshotFail,
    SnapshotResponse,
)
from app.services.snapshot import SnapshotService

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


def get_snapshot_service(
    session: Annotated[Session, Depends(get_database_session)],
) -> SnapshotService:
    return SnapshotService(session)


@router.get("", response_model=list[SnapshotResponse])
def list_snapshots(
    service: Annotated[SnapshotService, Depends(get_snapshot_service)],
    repository_uuid: Annotated[str | None, Query()] = None,
) -> list[SnapshotResponse]:
    return service.list_snapshots(repository_uuid)


@router.post("", response_model=SnapshotResponse, status_code=status.HTTP_201_CREATED)
def register_snapshot(
    payload: SnapshotCreate,
    service: Annotated[SnapshotService, Depends(get_snapshot_service)],
) -> SnapshotResponse:
    return service.register_snapshot(payload)


@router.post("/{snapshot_uuid}/start", response_model=SnapshotResponse)
def start_snapshot(
    snapshot_uuid: str,
    service: Annotated[SnapshotService, Depends(get_snapshot_service)],
) -> SnapshotResponse:
    return service.start_snapshot(snapshot_uuid)


@router.post("/{snapshot_uuid}/complete", response_model=SnapshotResponse)
def complete_snapshot(
    snapshot_uuid: str,
    payload: SnapshotComplete,
    service: Annotated[SnapshotService, Depends(get_snapshot_service)],
) -> SnapshotResponse:
    return service.complete_snapshot(snapshot_uuid, payload)


@router.post("/{snapshot_uuid}/fail", response_model=SnapshotResponse)
def fail_snapshot(
    snapshot_uuid: str,
    payload: SnapshotFail,
    service: Annotated[SnapshotService, Depends(get_snapshot_service)],
) -> SnapshotResponse:
    return service.fail_snapshot(snapshot_uuid, payload)
