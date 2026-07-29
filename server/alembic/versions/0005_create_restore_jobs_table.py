"""create restore jobs table

Revision ID: 0005_create_restore_jobs_table
Revises: 0004_create_scheduler_tables
Create Date: 2026-07-29 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_create_restore_jobs_table"
down_revision: str | None = "0004_create_scheduler_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "restore_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("target_path", sa.String(length=4096), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("verification_message", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["snapshot_id"],
            ["snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_restore_jobs_snapshot_id"),
        "restore_jobs",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(op.f("ix_restore_jobs_uuid"), "restore_jobs", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_restore_jobs_uuid"), table_name="restore_jobs")
    op.drop_index(op.f("ix_restore_jobs_snapshot_id"), table_name="restore_jobs")
    op.drop_table("restore_jobs")
