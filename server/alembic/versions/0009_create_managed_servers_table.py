"""create managed servers table

Revision ID: 0009_managed_servers
Revises: 0008_security
Create Date: 2026-08-01 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_managed_servers"
down_revision: str | None = "0008_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "managed_servers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ssh_port", sa.Integer(), nullable=False),
        sa.Column("ssh_username", sa.String(length=120), nullable=False),
        sa.Column("ssh_host_key_sha256", sa.String(length=128), nullable=True),
        sa.Column("client_path", sa.String(length=4096), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_managed_servers_uuid"),
        "managed_servers",
        ["uuid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_managed_servers_uuid"), table_name="managed_servers")
    op.drop_table("managed_servers")
