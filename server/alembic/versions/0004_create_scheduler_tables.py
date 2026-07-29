"""create scheduler tables

Revision ID: 0004_create_scheduler_tables
Revises: 0003_create_snapshots_table
Create Date: 2026-07-28 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_create_scheduler_tables"
down_revision: str | None = "0003_create_snapshots_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backup_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("engine", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=4096), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_backup_policies_repository_id"),
        "backup_policies",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backup_policies_uuid"),
        "backup_policies",
        ["uuid"],
        unique=True,
    )
    op.create_table(
        "backup_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("snapshot_uuid", sa.String(length=36), nullable=True),
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
            ["policy_id"],
            ["backup_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backup_jobs_policy_id"),
        "backup_jobs",
        ["policy_id"],
        unique=False,
    )
    op.create_index(op.f("ix_backup_jobs_uuid"), "backup_jobs", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_backup_jobs_uuid"), table_name="backup_jobs")
    op.drop_index(op.f("ix_backup_jobs_policy_id"), table_name="backup_jobs")
    op.drop_table("backup_jobs")
    op.drop_index(op.f("ix_backup_policies_uuid"), table_name="backup_policies")
    op.drop_index(
        op.f("ix_backup_policies_repository_id"),
        table_name="backup_policies",
    )
    op.drop_table("backup_policies")
