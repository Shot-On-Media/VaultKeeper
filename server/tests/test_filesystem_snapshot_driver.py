from __future__ import annotations

from pathlib import Path

from app.drivers.snapshot.filesystem import FilesystemSnapshotDriver


def test_filesystem_driver_scans_files(tmp_path: Path) -> None:
    (tmp_path / "one.txt").write_text("one", encoding="utf-8")
    nested_path = tmp_path / "nested"
    nested_path.mkdir()
    (nested_path / "two.txt").write_text("two", encoding="utf-8")

    result = FilesystemSnapshotDriver().scan(tmp_path)

    assert result.file_count == 2
    assert result.total_bytes == 6


def test_filesystem_driver_creates_compressed_tar(tmp_path: Path) -> None:
    source_path = tmp_path / "source"
    source_path.mkdir()
    (source_path / "data.txt").write_text("payload", encoding="utf-8")
    tar_path = tmp_path / "snapshot.tar"
    compressed_path = tmp_path / "snapshot.tar.zst"
    driver = FilesystemSnapshotDriver()

    driver.create_tar(source_path, tar_path)
    driver.compress_zstd(tar_path, compressed_path)

    assert tar_path.is_file()
    assert compressed_path.is_file()
    assert compressed_path.stat().st_size > 0
