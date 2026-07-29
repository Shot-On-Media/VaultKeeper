"""create verification reports table

Revision ID: 0006_verification_reports
Revises: 0005_create_restore_jobs_table
Create Date: 2026-07-29 11:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "0006_verification_reports"
down_revision: str | None = "0005_create_restore_jobs_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("verification_reports"):
        return

    op.create_table(
        "verification_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("checked_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_reports_repository_id"),
        "verification_reports",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_reports_snapshot_id"),
        "verification_reports",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_reports_uuid"),
        "verification_reports",
        ["uuid"],
        unique=True,
    )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("verification_reports"):
        return

    op.drop_index(
        op.f("ix_verification_reports_uuid"), table_name="verification_reports"
    )
    op.drop_index(
        op.f("ix_verification_reports_snapshot_id"),
        table_name="verification_reports",
    )
    op.drop_index(
        op.f("ix_verification_reports_repository_id"),
        table_name="verification_reports",
    )
    op.drop_table("verification_reports")
