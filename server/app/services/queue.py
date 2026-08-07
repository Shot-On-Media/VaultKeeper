from __future__ import annotations

import redis

from app.database.session import redis_client

BACKUP_QUEUE_NAME = "vaultkeeper:backup-jobs"


class BackupQueue:
    def __init__(self, client: redis.Redis = redis_client) -> None:
        self.client = client

    def enqueue(self, job_uuid: str) -> None:
        self.client.lpush(BACKUP_QUEUE_NAME, job_uuid)

    def dequeue(self) -> str | None:
        value = self.client.rpop(BACKUP_QUEUE_NAME)
        return str(value) if value is not None else None
