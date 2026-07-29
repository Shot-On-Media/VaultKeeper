from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.snapshot import Snapshot
from app.models.verification import VerificationReport
from app.repositories.repository import RepositoryRepository
from app.repositories.snapshot import SnapshotRepository
from app.repositories.verification import VerificationReportRepository
from app.schemas.snapshot import SnapshotStatus
from app.schemas.verification import (
    VerificationReportResponse,
    VerificationScope,
    VerificationStatus,
)
from app.services.checksum import sha256_file
from app.services.repository import REPOSITORY_DIRECTORIES


class VerificationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository_repository = RepositoryRepository(session)
        self.snapshot_repository = SnapshotRepository(session)
        self.verification_repository = VerificationReportRepository(session)

    def list_reports(self) -> list[VerificationReportResponse]:
        return [
            self._to_response(report) for report in self.verification_repository.list()
        ]

    def verify_repository(self, repository_uuid: str) -> VerificationReportResponse:
        repository = self._get_repository(repository_uuid)
        details: dict[str, Any] = {"layout": {}, "snapshots": []}
        failures: list[str] = []
        checked_count = 0

        repository_path = Path(repository.path)
        expected_metadata = {
            "uuid": repository.uuid,
            "name": repository.name,
            "storage_uuid": repository.storage.uuid,
            "repository_format": 1,
        }
        checked_count += self._verify_repository_layout(
            repository_path,
            expected_metadata,
            details,
            failures,
        )

        for snapshot in self.snapshot_repository.list(repository.uuid):
            snapshot_result = self._verify_snapshot(snapshot)
            details["snapshots"].append(snapshot_result)
            checked_count += 1
            if snapshot_result["status"] == VerificationStatus.FAILED.value:
                failures.append(
                    f"Snapshot {snapshot.uuid}: {snapshot_result['message']}"
                )

        report_status = (
            VerificationStatus.FAILED if failures else VerificationStatus.PASSED
        )
        message = (
            f"Repository verification failed with {len(failures)} issues."
            if failures
            else "Repository integrity verified."
        )
        return self._store_report(
            repository=repository,
            snapshot=None,
            scope=VerificationScope.REPOSITORY,
            status=report_status,
            checked_count=checked_count,
            failed_count=len(failures),
            message=message,
            details=details,
        )

    def verify_snapshot(self, snapshot_uuid: str) -> VerificationReportResponse:
        snapshot = self._get_snapshot(snapshot_uuid)
        details = self._verify_snapshot(snapshot)
        report_status = VerificationStatus(details["status"])
        return self._store_report(
            repository=snapshot.repository,
            snapshot=snapshot,
            scope=VerificationScope.SNAPSHOT,
            status=report_status,
            checked_count=1,
            failed_count=1 if report_status is VerificationStatus.FAILED else 0,
            message=str(details["message"]),
            details=details,
        )

    def _verify_repository_layout(
        self,
        repository_path: Path,
        expected_metadata: dict[str, Any],
        details: dict[str, Any],
        failures: list[str],
    ) -> int:
        checks = 0
        layout_details: dict[str, Any] = {}
        details["layout"] = layout_details
        if not repository_path.is_dir():
            failures.append("Repository path is missing.")
            layout_details["repository_path"] = "missing"
            return 1

        layout_details["repository_path"] = "present"
        for name in ("repository.json", *REPOSITORY_DIRECTORIES):
            checks += 1
            path = repository_path / name
            layout_details[name] = "present" if path.exists() else "missing"
            if not path.exists():
                failures.append(f"Repository layout is missing {name}.")

        metadata_path = repository_path / "repository.json"
        if metadata_path.is_file():
            checks += 1
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures.append("repository.json is not valid JSON.")
                layout_details["metadata"] = "invalid_json"
            else:
                mismatched = [
                    key
                    for key, expected in expected_metadata.items()
                    if metadata.get(key) != expected
                ]
                layout_details["metadata"] = {
                    "status": "matched" if not mismatched else "mismatched",
                    "mismatched_fields": mismatched,
                }
                if mismatched:
                    failures.append(
                        "repository.json metadata mismatch: "
                        + ", ".join(sorted(mismatched))
                    )
        return checks

    def _verify_snapshot(self, snapshot: Snapshot) -> dict[str, Any]:
        details: dict[str, Any] = {
            "snapshot_uuid": snapshot.uuid,
            "engine": snapshot.engine,
            "status": snapshot.status,
        }
        if SnapshotStatus(snapshot.status) is not SnapshotStatus.COMPLETED:
            return {
                **details,
                "status": VerificationStatus.WARNING.value,
                "message": "Snapshot is not completed.",
            }

        artifact_name = snapshot.manifest.get("artifact")
        if not isinstance(artifact_name, str) or artifact_name == "":
            return {
                **details,
                "status": VerificationStatus.FAILED.value,
                "message": "Snapshot manifest does not include an artifact.",
            }

        artifact_path = Path(snapshot.repository.path) / "snapshots" / artifact_name
        details["artifact"] = str(artifact_path)
        if not artifact_path.is_file():
            return {
                **details,
                "status": VerificationStatus.FAILED.value,
                "message": "Snapshot artifact is missing.",
            }

        actual_size = artifact_path.stat().st_size
        details["size_bytes"] = actual_size
        if snapshot.size_bytes is not None and snapshot.size_bytes != actual_size:
            return {
                **details,
                "status": VerificationStatus.FAILED.value,
                "message": "Snapshot artifact size does not match metadata.",
            }

        expected_checksum = snapshot.manifest.get("sha256")
        actual_checksum = sha256_file(artifact_path)
        details["sha256"] = actual_checksum
        if not isinstance(expected_checksum, str) or expected_checksum == "":
            return {
                **details,
                "status": VerificationStatus.WARNING.value,
                "message": "Snapshot artifact exists but has no stored checksum.",
            }
        if expected_checksum != actual_checksum:
            return {
                **details,
                "status": VerificationStatus.FAILED.value,
                "message": "Snapshot artifact checksum does not match manifest.",
            }

        return {
            **details,
            "status": VerificationStatus.PASSED.value,
            "message": "Snapshot artifact verified.",
        }

    def _store_report(
        self,
        repository: Repository,
        snapshot: Snapshot | None,
        scope: VerificationScope,
        status: VerificationStatus,
        checked_count: int,
        failed_count: int,
        message: str,
        details: dict[str, Any],
    ) -> VerificationReportResponse:
        report = VerificationReport(
            repository_id=repository.id,
            snapshot_id=snapshot.id if snapshot else None,
            scope=scope.value,
            status=status.value,
            checked_count=checked_count,
            failed_count=failed_count,
            message=message,
            details=details,
        )
        self.verification_repository.add(report)
        self.session.commit()
        self.session.refresh(report)
        return self._to_response(report)

    def _get_repository(self, repository_uuid: str) -> Repository:
        repository = self.repository_repository.get_by_uuid(repository_uuid)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found.",
            )
        return repository

    def _get_snapshot(self, snapshot_uuid: str) -> Snapshot:
        snapshot = self.snapshot_repository.get_by_uuid(snapshot_uuid)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found.",
            )
        return snapshot

    def _to_response(self, report: VerificationReport) -> VerificationReportResponse:
        return VerificationReportResponse(
            uuid=report.uuid,
            repository_uuid=report.repository.uuid,
            snapshot_uuid=report.snapshot.uuid if report.snapshot else None,
            scope=VerificationScope(report.scope),
            status=VerificationStatus(report.status),
            checked_count=report.checked_count,
            failed_count=report.failed_count,
            message=report.message,
            details=report.details,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
