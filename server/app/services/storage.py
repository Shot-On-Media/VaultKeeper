from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.drivers.storage.registry import get_storage_driver
from app.models.storage import Storage
from app.repositories.repository import RepositoryRepository
from app.repositories.storage import StorageRepository
from app.schemas.storage import (
    StorageCreate,
    StorageDriver,
    StorageResponse,
    StorageStatus,
    StorageUpdate,
    StorageValidationResponse,
)


class StorageService:
    def __init__(self, session: Session) -> None:
        self.repository = StorageRepository(session)
        self.repository_repository = RepositoryRepository(session)
        self.session = session

    def list_storage(self) -> list[StorageResponse]:
        return [self._to_response(storage) for storage in self.repository.list()]

    def create_storage(self, payload: StorageCreate) -> StorageResponse:
        self._ensure_name_available(payload.name)
        storage = Storage(
            name=payload.name,
            driver=payload.driver.value,
            config=payload.config.model_dump(),
            status=StorageStatus.UNKNOWN.value,
        )
        self.repository.add(storage)
        self.session.commit()
        self.session.refresh(storage)
        return self._to_response(storage)

    def update_storage(
        self,
        storage_uuid: str,
        payload: StorageUpdate,
    ) -> StorageResponse:
        storage = self._get_storage(storage_uuid)
        if payload.name is not None and payload.name != storage.name:
            self._ensure_name_available(payload.name)
            storage.name = payload.name
        if payload.config is not None:
            storage.config = payload.config.model_dump()
            storage.status = StorageStatus.UNKNOWN.value
            storage.last_validated_at = None
            storage.validation_message = None

        self.session.commit()
        self.session.refresh(storage)
        return self._to_response(storage)

    def delete_storage(self, storage_uuid: str) -> None:
        storage = self._get_storage(storage_uuid)
        if self.repository_repository.list_by_storage_uuid(storage_uuid):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Storage has repositories and cannot be deleted.",
            )
        self.repository.delete(storage)
        self.session.commit()

    def validate_storage(self, storage_uuid: str) -> StorageValidationResponse:
        storage = self._get_storage(storage_uuid)
        driver = get_storage_driver(StorageDriver(storage.driver))
        result = driver.validate(storage.config)
        validated_at = datetime.now(UTC)
        storage.status = (
            StorageStatus.VALID.value if result.valid else StorageStatus.INVALID.value
        )
        storage.last_validated_at = validated_at
        storage.validation_message = result.message
        self.session.commit()

        return StorageValidationResponse(
            uuid=storage.uuid,
            status=StorageStatus(storage.status),
            message=result.message,
            validated_at=validated_at,
        )

    def _get_storage(self, storage_uuid: str) -> Storage:
        storage = self.repository.get_by_uuid(storage_uuid)
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
                detail="Storage name already exists.",
            )

    def _to_response(self, storage: Storage) -> StorageResponse:
        return StorageResponse.model_validate(storage)
