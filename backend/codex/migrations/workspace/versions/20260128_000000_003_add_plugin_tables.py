"""Add plugin system tables

Revision ID: 003
Revises: 002
Create Date: 2026-01-28

This migration adds plugin system tables:
- plugins: Plugin registry table
- plugin_configs: Plugin configurations per workspace
- plugin_secrets: Secure plugin secrets (encrypted)
- plugin_api_logs: Plugin API request logs (for rate limiting and debugging)
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create plugins table
    if not table_exists("plugins"):
        op.create_table(
            "plugins",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("installed_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("manifest", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_plugins_plugin_id"), "plugins", ["plugin_id"], unique=True)

    # Create plugin_configs table
    if not table_exists("plugin_configs"):
        op.create_table(
            "plugin_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["plugin_id"], ["plugins.plugin_id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_plugin_configs_workspace_id"), "plugin_configs", ["workspace_id"])
        op.create_index(op.f("ix_plugin_configs_plugin_id"), "plugin_configs", ["plugin_id"])

    # Create plugin_secrets table
    if not table_exists("plugin_secrets"):
        op.create_table(
            "plugin_secrets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("encrypted_value", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["plugin_id"], ["plugins.plugin_id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_plugin_secrets_workspace_id"), "plugin_secrets", ["workspace_id"])
        op.create_index(op.f("ix_plugin_secrets_plugin_id"), "plugin_secrets", ["plugin_id"])

    # Create plugin_api_logs table
    if not table_exists("plugin_api_logs"):
        op.create_table(
            "plugin_api_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("endpoint_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["plugin_id"], ["plugins.plugin_id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_plugin_api_logs_workspace_id"), "plugin_api_logs", ["workspace_id"])
        op.create_index(op.f("ix_plugin_api_logs_plugin_id"), "plugin_api_logs", ["plugin_id"])
        op.create_index(op.f("ix_plugin_api_logs_timestamp"), "plugin_api_logs", ["timestamp"])


def downgrade() -> None:
    # Drop plugin tables in reverse order
    if table_exists("plugin_api_logs"):
        op.drop_index(op.f("ix_plugin_api_logs_timestamp"), table_name="plugin_api_logs")
        op.drop_index(op.f("ix_plugin_api_logs_plugin_id"), table_name="plugin_api_logs")
        op.drop_index(op.f("ix_plugin_api_logs_workspace_id"), table_name="plugin_api_logs")
        op.drop_table("plugin_api_logs")
    
    if table_exists("plugin_secrets"):
        op.drop_index(op.f("ix_plugin_secrets_plugin_id"), table_name="plugin_secrets")
        op.drop_index(op.f("ix_plugin_secrets_workspace_id"), table_name="plugin_secrets")
        op.drop_table("plugin_secrets")
    
    if table_exists("plugin_configs"):
        op.drop_index(op.f("ix_plugin_configs_plugin_id"), table_name="plugin_configs")
        op.drop_index(op.f("ix_plugin_configs_workspace_id"), table_name="plugin_configs")
        op.drop_table("plugin_configs")
    
    if table_exists("plugins"):
        op.drop_index(op.f("ix_plugins_plugin_id"), table_name="plugins")
        op.drop_table("plugins")
