from __future__ import annotations

from pathlib import Path

from app.drivers.storage.local_filesystem import LocalFilesystemStorageDriver


def test_local_filesystem_driver_accepts_writable_directory(tmp_path: Path) -> None:
    result = LocalFilesystemStorageDriver().validate({"path": str(tmp_path)})

    assert result.valid is True
    assert result.message == "Storage path is reachable and writable."


def test_local_filesystem_driver_rejects_missing_directory(tmp_path: Path) -> None:
    result = LocalFilesystemStorageDriver().validate(
        {"path": str(tmp_path / "missing")}
    )

    assert result.valid is False
    assert result.message == "Path does not exist."
