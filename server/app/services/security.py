from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.security import APIKey, AuditLog
from app.repositories.security import APIKeyRepository, AuditLogRepository
from app.schemas.security import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
    AuditLogResponse,
    LoginRequest,
    Principal,
    TokenResponse,
)


class SecurityService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.api_key_repository = APIKeyRepository(session)
        self.audit_log_repository = AuditLogRepository(session)

    def login(self, payload: LoginRequest) -> TokenResponse:
        valid_username = hmac.compare_digest(
            payload.username,
            self.settings.admin_username,
        )
        valid_password = hmac.compare_digest(
            payload.password,
            self.settings.admin_password,
        )
        if not valid_username or not valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.access_token_minutes
        )
        return TokenResponse(
            access_token=self.create_token(
                Principal(actor=payload.username, auth_type="password"),
                expires_at,
            ),
            expires_at=expires_at,
        )

    def create_token(self, principal: Principal, expires_at: datetime) -> str:
        payload = {
            "actor": principal.actor,
            "auth_type": principal.auth_type,
            "exp": int(expires_at.timestamp()),
        }
        encoded_payload = self._base64url_encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signature = self._sign(encoded_payload.encode("ascii"))
        return f"{encoded_payload}.{signature}"

    def verify_token(self, token: str) -> Principal:
        try:
            encoded_payload, signature = token.split(".", 1)
        except ValueError as exc:
            raise self._unauthorized() from exc
        expected_signature = self._sign(encoded_payload.encode("ascii"))
        if not hmac.compare_digest(signature, expected_signature):
            raise self._unauthorized()
        try:
            payload = self._base64url_decode(encoded_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            raise self._unauthorized() from exc
        expires_at = int(payload.get("exp", 0))
        if expires_at < int(datetime.now(UTC).timestamp()):
            raise self._unauthorized()
        actor = payload.get("actor")
        auth_type = payload.get("auth_type")
        if not isinstance(actor, str) or not isinstance(auth_type, str):
            raise self._unauthorized()
        return Principal(actor=actor, auth_type=auth_type)

    def list_api_keys(self) -> list[APIKeyResponse]:
        return [
            self._api_key_to_response(api_key)
            for api_key in self.api_key_repository.list()
        ]

    def create_api_key(self, payload: APIKeyCreate) -> APIKeyCreateResponse:
        if self.api_key_repository.get_by_name(payload.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="API key name already exists.",
            )
        secret = f"vk_{secrets.token_urlsafe(32)}"
        api_key = APIKey(
            name=payload.name,
            key_hash=self.hash_secret(secret),
            key_prefix=secret[:12],
            enabled=payload.enabled,
        )
        self.api_key_repository.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        response = self._api_key_to_response(api_key).model_dump()
        return APIKeyCreateResponse(**response, secret=secret)

    def update_api_key(
        self,
        api_key_uuid: str,
        payload: APIKeyUpdate,
    ) -> APIKeyResponse:
        api_key = self._get_api_key(api_key_uuid)
        if payload.name is not None and payload.name != api_key.name:
            if self.api_key_repository.get_by_name(payload.name) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="API key name already exists.",
                )
            api_key.name = payload.name
        if payload.enabled is not None:
            api_key.enabled = payload.enabled
        self.session.commit()
        self.session.refresh(api_key)
        return self._api_key_to_response(api_key)

    def delete_api_key(self, api_key_uuid: str) -> None:
        api_key = self._get_api_key(api_key_uuid)
        self.api_key_repository.delete(api_key)
        self.session.commit()

    def principal_from_api_key(self, secret: str) -> Principal | None:
        api_key = self.api_key_repository.get_by_hash(self.hash_secret(secret))
        if api_key is None or not api_key.enabled:
            return None
        api_key.last_used_at = datetime.now(UTC)
        self.session.commit()
        return Principal(actor=f"api-key:{api_key.name}", auth_type="api_key")

    def list_audit_logs(self) -> list[AuditLogResponse]:
        return [
            self._audit_log_to_response(audit_log)
            for audit_log in self.audit_log_repository.list()
        ]

    def record_audit(
        self,
        actor: str,
        action: str,
        path: str,
        method: str,
        status_code: int,
        client_host: str | None,
        message: str | None = None,
    ) -> None:
        self.audit_log_repository.add(
            AuditLog(
                actor=actor,
                action=action,
                path=path,
                method=method,
                status_code=status_code,
                client_host=client_host,
                message=message,
            )
        )
        self.session.commit()

    def hash_secret(self, secret: str) -> str:
        return hmac.new(
            self.settings.security_secret.encode("utf-8"),
            secret.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _get_api_key(self, api_key_uuid: str) -> APIKey:
        api_key = self.api_key_repository.get_by_uuid(api_key_uuid)
        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found.",
            )
        return api_key

    def _sign(self, payload: bytes) -> str:
        signature = hmac.new(
            self.settings.security_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()
        return self._base64url_encode(signature)

    def _base64url_encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    def _base64url_decode(self, value: str) -> dict[str, Any]:
        padded = value + "=" * (-len(value) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))

    def _api_key_to_response(self, api_key: APIKey) -> APIKeyResponse:
        return APIKeyResponse(
            uuid=api_key.uuid,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            enabled=api_key.enabled,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
        )

    def _audit_log_to_response(self, audit_log: AuditLog) -> AuditLogResponse:
        return AuditLogResponse(
            uuid=audit_log.uuid,
            actor=audit_log.actor,
            action=audit_log.action,
            path=audit_log.path,
            method=audit_log.method,
            status_code=audit_log.status_code,
            client_host=audit_log.client_host,
            message=audit_log.message,
            created_at=audit_log.created_at,
            updated_at=audit_log.updated_at,
        )

    def _unauthorized(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
