from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.storage import Storage
from app.repositories.repository import RepositoryRepository
from app.repositories.storage import StorageRepository
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
    RepositoryStatus,
    RepositoryUpdate,
    RepositoryValidationResponse,
)
from app.schemas.storage import StorageDriver

REPOSITORY_DIRECTORIES = ("snapshots", "logs", "verify", "temp", "locks")


class RepositoryService:
    def __init__(self, session: Session) -> None:
        self.repository = RepositoryRepository(session)
        self.storage_repository = StorageRepository(session)
        self.session = session

    def list_repositories(self) -> list[RepositoryResponse]:
        return [self._to_response(repository) for repository in self.repository.list()]

    def create_repository(self, payload: RepositoryCreate) -> RepositoryResponse:
        self._ensure_name_available(payload.name)
        storage = self._get_storage(payload.storage_uuid)
        root_path = self._storage_root(storage)

        repository = Repository(
            storage_id=storage.id,
            name=payload.name,
            path="",
            status=RepositoryStatus.UNKNOWN.value,
        )
        self.repository.add(repository)
        repository_path = root_path / repository.uuid
        self._create_repository_layout(repository_path, repository, storage)
        repository.path = str(repository_path)
        repository.status = RepositoryStatus.VALID.value
        repository.last_validated_at = datetime.now(UTC)
        repository.validation_message = "Repository layout created."
        self.session.commit()
        self.session.refresh(repository)
        return self._to_response(repository)

    def update_repository(
        self,
        repository_uuid: str,
        payload: RepositoryUpdate,
    ) -> RepositoryResponse:
        repository = self._get_repository(repository_uuid)
        if payload.name != repository.name:
            self._ensure_name_available(payload.name)
            repository.name = payload.name
            self._write_repository_metadata(Path(repository.path), repository)
        self.session.commit()
        self.session.refresh(repository)
        return self._to_response(repository)

    def delete_repository(self, repository_uuid: str) -> None:
        repository = self._get_repository(repository_uuid)
        self.repository.delete(repository)
        self.session.commit()

    def validate_repository(
        self,
        repository_uuid: str,
    ) -> RepositoryValidationResponse:
        repository = self._get_repository(repository_uuid)
        repository_path = Path(repository.path)
        missing_paths = [
            name
            for name in ("repository.json", *REPOSITORY_DIRECTORIES)
            if not (repository_path / name).exists()
        ]
        validated_at = datetime.now(UTC)

        if repository_path.is_dir() and not missing_paths:
            repository.status = RepositoryStatus.VALID.value
            message = "Repository layout is valid."
        else:
            repository.status = RepositoryStatus.INVALID.value
            missing = (
                ", ".join(missing_paths) if missing_paths else str(repository_path)
            )
            message = f"Repository layout is incomplete: {missing}."

        repository.last_validated_at = validated_at
        repository.validation_message = message
        self.session.commit()

        return RepositoryValidationResponse(
            uuid=repository.uuid,
            status=RepositoryStatus(repository.status),
            message=message,
            validated_at=validated_at,
        )

    def _create_repository_layout(
        self,
        repository_path: Path,
        repository: Repository,
        storage: Storage,
    ) -> None:
        repository_path.mkdir(mode=0o750, parents=False, exist_ok=False)
        for directory_name in REPOSITORY_DIRECTORIES:
            (repository_path / directory_name).mkdir(mode=0o750)
        self._write_repository_metadata(repository_path, repository, storage)

    def _write_repository_metadata(
        self,
        repository_path: Path,
        repository: Repository,
        storage: Storage | None = None,
    ) -> None:
        metadata = {
            "uuid": repository.uuid,
            "name": repository.name,
            "storage_uuid": storage.uuid if storage else repository.storage.uuid,
            "repository_format": 1,
            "created_at": repository.created_at.isoformat(),
        }
        (repository_path / "repository.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _storage_root(self, storage: Storage) -> Path:
        if storage.driver != StorageDriver.LOCAL_FILESYSTEM.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Storage driver is not supported for repository creation.",
            )

        path = storage.config.get("path")
        if not isinstance(path, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Storage path is invalid.",
            )
        root_path = Path(path)
        if not root_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Storage path does not exist.",
            )
        return root_path

    def _get_repository(self, repository_uuid: str) -> Repository:
        repository = self.repository.get_by_uuid(repository_uuid)
        if repository is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found.",
            )
        return repository

    def _get_storage(self, storage_uuid: str) -> Storage:
        storage = self.storage_repository.get_by_uuid(storage_uuid)
        if storage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage not found.",
            )
        return storage

    def _ensure_name_available(self, name: str) -> None:
        if self.repository.get_by_name(name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository name already exists.",
            )

    def _to_response(self, repository: Repository) -> RepositoryResponse:
        return RepositoryResponse(
            uuid=repository.uuid,
            storage_uuid=repository.storage.uuid,
            name=repository.name,
            path=repository.path,
            status=RepositoryStatus(repository.status),
            last_validated_at=repository.last_validated_at,
            validation_message=repository.validation_message,
            created_at=repository.created_at,
            updated_at=repository.updated_at,
        )
