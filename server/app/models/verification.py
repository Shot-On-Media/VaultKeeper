from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin


class VerificationReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("snapshots.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    checked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    repository = relationship("Repository")
    snapshot = relationship("Snapshot")
