"""Add version column to plugin config tables

Revision ID: 013
Revises: 012
Create Date: 2026-02-27

Adds a nullable version column to plugin_configs and notebook_plugin_configs
so workspaces and notebooks can pin a specific plugin version. NULL means
"use the latest available version".
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plugin_configs", sa.Column("version", sa.String(), nullable=True))
    op.add_column("notebook_plugin_configs", sa.Column("version", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("notebook_plugin_configs", "version")
    op.drop_column("plugin_configs", "version")
