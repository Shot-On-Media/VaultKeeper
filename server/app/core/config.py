from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VK_",
        extra="ignore",
    )

    app_name: str = "VaultKeeper API"
    app_version: str = "0.1.0-alpha1"
    app_codename: str = "Foundation"
    app_env: str = "development"
    db_host: str = "mariadb"
    db_port: int = 3306
    db_name: str = "vaultkeeper"
    db_user: str = "vaultkeeper"
    db_password: str = Field(default="change-me", repr=False)
    redis_url: str = "redis://redis:6379/0"
    scheduler_enabled: bool = False
    scheduler_interval_seconds: int = 60

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
