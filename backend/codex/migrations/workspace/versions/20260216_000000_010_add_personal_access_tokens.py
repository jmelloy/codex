"""Add personal access tokens table

Revision ID: 010
Revises: 009
Create Date: 2026-02-16

This migration adds the personal_access_tokens table for API token authentication,
enabling programmatic access from scripts, pre-commit hooks, etc.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not table_exists("personal_access_tokens"):
        op.create_table(
            "personal_access_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("token_prefix", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("scopes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=True),
            sa.Column("notebook_id", sa.Integer(), sa.ForeignKey("notebooks.id"), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_personal_access_tokens_user_id", "personal_access_tokens", ["user_id"])
        op.create_index("ix_personal_access_tokens_token_hash", "personal_access_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    if table_exists("personal_access_tokens"):
        op.drop_index("ix_personal_access_tokens_token_hash", table_name="personal_access_tokens")
        op.drop_index("ix_personal_access_tokens_user_id", table_name="personal_access_tokens")
        op.drop_table("personal_access_tokens")
