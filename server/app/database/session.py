from __future__ import annotations

from collections.abc import Generator

import redis
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine: Engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)
redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_database_session() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
