from __future__ import annotations

from pathlib import Path

from app.drivers.storage.base import StorageValidationResult


class LocalFilesystemStorageDriver:
    def validate(self, config: dict[str, object]) -> StorageValidationResult:
        raw_path = config.get("path")
        if not isinstance(raw_path, str):
            return StorageValidationResult(False, "Local filesystem path is required.")

        path = Path(raw_path)
        if not path.is_absolute():
            return StorageValidationResult(False, "Path must be absolute.")
        if not path.exists():
            return StorageValidationResult(False, "Path does not exist.")
        if not path.is_dir():
            return StorageValidationResult(False, "Path is not a directory.")

        probe_path = path / ".vaultkeeper-write-test"
        try:
            probe_path.write_text("ok", encoding="utf-8")
            probe_path.unlink()
        except OSError as exc:
            return StorageValidationResult(False, f"Path is not writable: {exc}")

        return StorageValidationResult(True, "Storage path is reachable and writable.")
