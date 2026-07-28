from __future__ import annotations

from pathlib import Path

from app.drivers.snapshot.mariadb import MariaDBConnectionConfig, MariaDBSnapshotDriver


def test_mariadb_driver_compresses_dump(tmp_path: Path) -> None:
    dump_path = tmp_path / "database.sql"
    compressed_path = tmp_path / "database.sql.zst"
    dump_path.write_text("CREATE TABLE example (id int);\n", encoding="utf-8")

    MariaDBSnapshotDriver().compress_zstd(dump_path, compressed_path)

    assert compressed_path.is_file()
    assert compressed_path.stat().st_size > 0


def test_mariadb_connection_config_is_typed() -> None:
    config = MariaDBConnectionConfig(
        host="mariadb",
        port=3306,
        user="vaultkeeper",
        password="secret",
    )

    assert config.host == "mariadb"
    assert config.port == 3306
