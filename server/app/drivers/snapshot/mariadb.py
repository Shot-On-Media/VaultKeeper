from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pymysql
import zstandard


@dataclass(frozen=True)
class MariaDBConnectionConfig:
    host: str
    port: int
    user: str
    password: str


class MariaDBSnapshotDriver:
    def __init__(self, dump_binary: str = "mysqldump") -> None:
        self.dump_binary = dump_binary

    def discover_databases(self, config: MariaDBConnectionConfig) -> list[str]:
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                database_names = [str(row[0]) for row in cursor.fetchall()]
        finally:
            connection.close()

        system_databases = {"information_schema", "mysql", "performance_schema", "sys"}
        return [
            database_name
            for database_name in database_names
            if database_name not in system_databases
        ]

    def dump_database(
        self,
        config: MariaDBConnectionConfig,
        database_name: str,
        dump_path: Path,
    ) -> None:
        environment = os.environ.copy()
        environment["MYSQL_PWD"] = config.password
        command = [
            self.dump_binary,
            "--host",
            config.host,
            "--port",
            str(config.port),
            "--user",
            config.user,
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            database_name,
        ]
        with dump_path.open("wb") as destination_file:
            subprocess.run(
                command,
                check=True,
                env=environment,
                stdout=destination_file,
                stderr=subprocess.PIPE,
            )

    def compress_zstd(self, dump_path: Path, compressed_path: Path) -> None:
        compressor = zstandard.ZstdCompressor(level=3)
        with dump_path.open("rb") as source_file:
            with compressed_path.open("wb") as destination_file:
                compressor.copy_stream(source_file, destination_file)
