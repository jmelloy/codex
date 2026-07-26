"""Use TIMESTAMP WITH TIME ZONE for all datetime columns

Revision ID: 012
Revises: 011
Create Date: 2026-02-20

PostgreSQL requires TIMESTAMPTZ columns when inserting timezone-aware
datetime values. This migration alters all TIMESTAMP columns to
TIMESTAMP WITH TIME ZONE.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# All (table, column) pairs that need to be altered
TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("workspaces", "created_at"),
    ("workspaces", "updated_at"),
    ("workspace_permissions", "created_at"),
    ("tasks", "created_at"),
    ("tasks", "updated_at"),
    ("tasks", "completed_at"),
    ("notebooks", "created_at"),
    ("notebooks", "updated_at"),
    ("plugins", "installed_at"),
    ("plugins", "updated_at"),
    ("plugin_configs", "created_at"),
    ("plugin_configs", "updated_at"),
    ("notebook_plugin_configs", "created_at"),
    ("notebook_plugin_configs", "updated_at"),
    ("plugin_secrets", "created_at"),
    ("plugin_secrets", "updated_at"),
    ("plugin_api_logs", "timestamp"),
    ("agents", "created_at"),
    ("agents", "updated_at"),
    ("agent_credentials", "created_at"),
    ("agent_sessions", "started_at"),
    ("agent_sessions", "completed_at"),
    ("agent_action_logs", "created_at"),
    ("personal_access_tokens", "last_used_at"),
    ("personal_access_tokens", "expires_at"),
    ("personal_access_tokens", "created_at"),
    ("oauth_connections", "token_expires_at"),
    ("oauth_connections", "created_at"),
    ("oauth_connections", "updated_at"),
    ("integration_artifacts", "fetched_at"),
    ("integration_artifacts", "expires_at"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # Only PostgreSQL distinguishes TIMESTAMP vs TIMESTAMPTZ
        return

    for table, column in TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table, column in TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
