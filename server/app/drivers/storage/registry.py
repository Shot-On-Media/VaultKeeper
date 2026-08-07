from __future__ import annotations

from app.drivers.storage.local_filesystem import LocalFilesystemStorageDriver
from app.schemas.storage import StorageDriver


def get_storage_driver(driver_name: StorageDriver) -> LocalFilesystemStorageDriver:
    drivers: dict[StorageDriver, LocalFilesystemStorageDriver] = {
        StorageDriver.LOCAL_FILESYSTEM: LocalFilesystemStorageDriver(),
    }
    return drivers[driver_name]
