"""Add plugin enable/disable at workspace and notebook levels

Revision ID: 004
Revises: 003
Create Date: 2026-01-30

This migration adds:
- enabled field to plugin_configs for workspace-level plugin disabling
- notebook_plugin_configs table for notebook-level plugin preferences
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add enabled field to plugin_configs if it doesn't exist
    if table_exists("plugin_configs") and not column_exists("plugin_configs", "enabled"):
        op.add_column(
            "plugin_configs",
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        )

    # Create notebook_plugin_configs table
    if not table_exists("notebook_plugin_configs"):
        op.create_table(
            "notebook_plugin_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("notebook_id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"]),
            sa.ForeignKeyConstraint(["plugin_id"], ["plugins.plugin_id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_notebook_plugin_configs_notebook_id"),
            "notebook_plugin_configs",
            ["notebook_id"],
        )
        op.create_index(
            op.f("ix_notebook_plugin_configs_plugin_id"),
            "notebook_plugin_configs",
            ["plugin_id"],
        )


def downgrade() -> None:
    # Drop notebook_plugin_configs table
    if table_exists("notebook_plugin_configs"):
        op.drop_index(
            op.f("ix_notebook_plugin_configs_plugin_id"),
            table_name="notebook_plugin_configs",
        )
        op.drop_index(
            op.f("ix_notebook_plugin_configs_notebook_id"),
            table_name="notebook_plugin_configs",
        )
        op.drop_table("notebook_plugin_configs")

    # Remove enabled field from plugin_configs
    if table_exists("plugin_configs") and column_exists("plugin_configs", "enabled"):
        op.drop_column("plugin_configs", "enabled")
