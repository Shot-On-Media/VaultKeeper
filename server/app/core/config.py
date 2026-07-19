from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    db_name: str
    db_user: str
    db_password: str = Field(repr=False)
    redis_url: str = "redis://redis:6379/0"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
