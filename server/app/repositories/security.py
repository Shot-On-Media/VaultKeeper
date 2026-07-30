from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.security import APIKey, AuditLog


class APIKeyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[APIKey]:
        return list(self.session.scalars(select(APIKey).order_by(APIKey.name)))

    def get_by_uuid(self, api_key_uuid: str) -> APIKey | None:
        return self.session.scalar(select(APIKey).where(APIKey.uuid == api_key_uuid))

    def get_by_name(self, name: str) -> APIKey | None:
        return self.session.scalar(select(APIKey).where(APIKey.name == name))

    def get_by_hash(self, key_hash: str) -> APIKey | None:
        return self.session.scalar(select(APIKey).where(APIKey.key_hash == key_hash))

    def add(self, api_key: APIKey) -> APIKey:
        self.session.add(api_key)
        self.session.flush()
        self.session.refresh(api_key)
        return api_key

    def delete(self, api_key: APIKey) -> None:
        self.session.delete(api_key)
        self.session.flush()


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[AuditLog]:
        return list(
            self.session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()))
        )

    def add(self, audit_log: AuditLog) -> AuditLog:
        self.session.add(audit_log)
        self.session.flush()
        self.session.refresh(audit_log)
        return audit_log
