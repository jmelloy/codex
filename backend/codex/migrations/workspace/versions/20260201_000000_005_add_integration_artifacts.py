"""Add integration_artifacts table for caching API responses

Revision ID: 005
Revises: 004
Create Date: 2026-02-01

This migration adds:
- integration_artifacts table for caching integration API responses
  used by the /render endpoint for frontend-driven block rendering

Artifacts are stored in the filesystem at:
  {workspace_path}/.codex/artifacts/{plugin_id}/{hash}.json

The database only stores metadata and the path to the artifact file.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create integration_artifacts table
    if not table_exists("integration_artifacts"):
        op.create_table(
            "integration_artifacts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("plugin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("block_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("parameters_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("artifact_path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("fetched_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["plugin_id"], ["plugins.plugin_id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_integration_artifacts_workspace_id"),
            "integration_artifacts",
            ["workspace_id"],
        )
        op.create_index(
            op.f("ix_integration_artifacts_plugin_id"),
            "integration_artifacts",
            ["plugin_id"],
        )
        op.create_index(
            op.f("ix_integration_artifacts_block_type"),
            "integration_artifacts",
            ["block_type"],
        )
        op.create_index(
            op.f("ix_integration_artifacts_parameters_hash"),
            "integration_artifacts",
            ["parameters_hash"],
        )


def downgrade() -> None:
    # Drop integration_artifacts table
    if table_exists("integration_artifacts"):
        op.drop_index(
            op.f("ix_integration_artifacts_parameters_hash"),
            table_name="integration_artifacts",
        )
        op.drop_index(
            op.f("ix_integration_artifacts_block_type"),
            table_name="integration_artifacts",
        )
        op.drop_index(
            op.f("ix_integration_artifacts_plugin_id"),
            table_name="integration_artifacts",
        )
        op.drop_index(
            op.f("ix_integration_artifacts_workspace_id"),
            table_name="integration_artifacts",
        )
        op.drop_table("integration_artifacts")
