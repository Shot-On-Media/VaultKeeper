"""create snapshots table

Revision ID: 0003_create_snapshots_table
Revises: 0002_create_repositories_table
Create Date: 2026-07-22 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_create_snapshots_table"
down_revision: str | None = "0002_create_repositories_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("engine", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=4096), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
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
    )
    op.create_index(
        op.f("ix_snapshots_repository_id"),
        "snapshots",
        ["repository_id"],
        unique=False,
    )
    op.create_index(op.f("ix_snapshots_uuid"), "snapshots", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_snapshots_uuid"), table_name="snapshots")
    op.drop_index(op.f("ix_snapshots_repository_id"), table_name="snapshots")
    op.drop_table("snapshots")
