from __future__ import annotations

from app.core.config import Settings


def test_database_url_escapes_special_characters() -> None:
    settings = Settings(
        db_name="vaultkeeper",
        db_user="vaultkeeper",
        db_password="secret@value",
        db_host="mariadb",
        db_port=3306,
    )

    assert (
        settings.database_url
        == "mysql+pymysql://vaultkeeper:secret%40value@mariadb:3306/vaultkeeper"
    )
