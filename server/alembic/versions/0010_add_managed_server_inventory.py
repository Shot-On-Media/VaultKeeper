"""add managed server inventory

Revision ID: 0010_managed_server_inventory
Revises: 0009_managed_servers
Create Date: 2026-08-01 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_managed_server_inventory"
down_revision: str | None = "0009_managed_servers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "managed_servers",
        sa.Column("inventory", sa.JSON(), nullable=True),
    )
    op.execute("UPDATE managed_servers SET inventory = '{}' WHERE inventory IS NULL")
    op.alter_column(
        "managed_servers",
        "inventory",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.add_column(
        "managed_servers",
        sa.Column("last_inventory_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("managed_servers", "last_inventory_at")
    op.drop_column("managed_servers", "inventory")
