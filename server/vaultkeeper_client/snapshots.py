from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import BinaryIO

import zstandard


def stream_filesystem_snapshot(source_path: Path, output: BinaryIO) -> dict[str, int]:
    scan_result = _scan_filesystem(source_path)
    with tempfile.NamedTemporaryFile(suffix=".tar") as tar_file:
        tar_path = Path(tar_file.name)
        with tarfile.open(tar_path, mode="w") as archive:
            archive.add(source_path, arcname=source_path.name)
        _compress_file_to_stream(tar_path, output)
    return scan_result


def stream_mariadb_snapshot(
    host: str,
    port: int,
    user: str,
    password: str,
    database_name: str,
    output: BinaryIO,
    dump_binary: str = "mariadb-dump",
) -> dict[str, int]:
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = password
    command = [
        dump_binary,
        "--host",
        host,
        "--port",
        str(port),
        "--user",
        user,
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        database_name,
    ]
    with tempfile.NamedTemporaryFile(suffix=".sql") as dump_file:
        dump_path = Path(dump_file.name)
        with dump_path.open("wb") as destination:
            subprocess.run(
                command,
                check=True,
                env=environment,
                stdout=destination,
                stderr=subprocess.PIPE,
            )
        dump_bytes = dump_path.stat().st_size
        _compress_file_to_stream(dump_path, output)
    return {"source_bytes": dump_bytes}


def print_snapshot_metadata(metadata: dict[str, int | str]) -> None:
    print(json.dumps(metadata, sort_keys=True), file=os.sys.stderr)


def _scan_filesystem(source_path: Path) -> dict[str, int]:
    file_count = 0
    total_bytes = 0
    for path in source_path.rglob("*"):
        if path.is_file():
            file_count += 1
            total_bytes += path.stat().st_size
    return {"file_count": file_count, "source_bytes": total_bytes}


def _compress_file_to_stream(source_path: Path, output: BinaryIO) -> None:
    compressor = zstandard.ZstdCompressor(level=3)
    with source_path.open("rb") as source:
        compressor.copy_stream(source, output)
