"""Add oauth_connections table

Revision ID: 011
Revises: 010
Create Date: 2026-02-16

This migration adds the oauth_connections table for storing OAuth tokens
from external providers (Google, etc.) linked to user accounts.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not table_exists("oauth_connections"):
        op.create_table(
            "oauth_connections",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("provider_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("provider_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("access_token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("refresh_token", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(), nullable=True),
            sa.Column("scopes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_oauth_connections_user_id", "oauth_connections", ["user_id"])
        op.create_index("ix_oauth_connections_provider", "oauth_connections", ["provider"])


def downgrade() -> None:
    if table_exists("oauth_connections"):
        op.drop_index("ix_oauth_connections_provider", table_name="oauth_connections")
        op.drop_index("ix_oauth_connections_user_id", table_name="oauth_connections")
        op.drop_table("oauth_connections")
