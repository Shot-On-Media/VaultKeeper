from __future__ import annotations

import tarfile
from dataclasses import dataclass
from pathlib import Path

import zstandard


@dataclass(frozen=True)
class FilesystemScanResult:
    file_count: int
    total_bytes: int


class FilesystemSnapshotDriver:
    def scan(self, source_path: Path) -> FilesystemScanResult:
        file_count = 0
        total_bytes = 0
        for path in source_path.rglob("*"):
            if path.is_file():
                file_count += 1
                total_bytes += path.stat().st_size
        return FilesystemScanResult(file_count=file_count, total_bytes=total_bytes)

    def create_tar(self, source_path: Path, tar_path: Path) -> None:
        with tarfile.open(tar_path, mode="w") as archive:
            archive.add(source_path, arcname=source_path.name)

    def compress_zstd(self, tar_path: Path, compressed_path: Path) -> None:
        compressor = zstandard.ZstdCompressor(level=3)
        with tar_path.open("rb") as source_file:
            with compressed_path.open("wb") as destination_file:
                compressor.copy_stream(source_file, destination_file)
