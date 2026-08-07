from __future__ import annotations

import asyncio

import redis
import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import SessionLocal
from app.services.scheduler import SchedulerService
from app.workers.backup_worker import BackupWorker

logger = structlog.get_logger(__name__)


async def run_scheduler_loop(interval_seconds: int) -> None:
    while True:
        try:
            with SessionLocal() as session:
                SchedulerService(session).enqueue_due_policies()
                BackupWorker(session).process_next()
        except (SQLAlchemyError, redis.RedisError) as exc:
            logger.warning("scheduler_loop_failed", error=str(exc))
        await asyncio.sleep(interval_seconds)
