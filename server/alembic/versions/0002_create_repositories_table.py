"""create repositories table

Revision ID: 0002_create_repositories_table
Revises: 0001_create_storage_table
Create Date: 2026-07-22 13:10:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_create_repositories_table"
down_revision: str | None = "0001_create_storage_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("storage_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["storage_id"], ["storage.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_repositories_storage_id"),
        "repositories",
        ["storage_id"],
        unique=False,
    )
    op.create_index(op.f("ix_repositories_uuid"), "repositories", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_repositories_uuid"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_storage_id"), table_name="repositories")
    op.drop_table("repositories")
