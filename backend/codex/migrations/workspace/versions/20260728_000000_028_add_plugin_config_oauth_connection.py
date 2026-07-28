"""Add oauth_connection_id to plugin_configs

Revision ID: 028
Revises: 027
Create Date: 2026-07-28

Explicit integration identity for shared workspaces (issue #546, design doc §1
L12 / §7): a `PluginConfig` for an OAuth-backed integration must bind to one
explicit `OAuthConnection`, chosen by a workspace admin, rather than execution
implicitly picking whichever member happens to have a connection for that
provider. The column is nullable -- an integration with no binding simply
can't execute (`not_configured`), which is exactly the safe failure mode; no
existing row needs backfilling since no OAuth-backed integration plugin
exists yet.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in result)
    inspector = sa.inspect(conn)
    return any(col["name"] == column for col in inspector.get_columns(table))


def _index_exists(table: str, index_name: str) -> bool:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        result = conn.execute(sa.text(f"PRAGMA index_list({table})"))
        return any(row[1] == index_name for row in result)
    inspector = sa.inspect(conn)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def upgrade() -> None:
    if not _column_exists("plugin_configs", "oauth_connection_id"):
        op.add_column("plugin_configs", sa.Column("oauth_connection_id", sa.Integer(), nullable=True))
        with op.batch_alter_table("plugin_configs") as batch_op:
            batch_op.create_foreign_key(
                "fk_plugin_configs_oauth_connection_id_oauth_connections",
                "oauth_connections",
                ["oauth_connection_id"],
                ["id"],
            )
        # Batch mode recreates the table (SQLite has no native ALTER for FK/constraints),
        # which drops any index created beforehand -- so the index must run after the batch block.
        op.create_index("ix_plugin_configs_oauth_connection_id", "plugin_configs", ["oauth_connection_id"])
    elif not _index_exists("plugin_configs", "ix_plugin_configs_oauth_connection_id"):
        op.create_index("ix_plugin_configs_oauth_connection_id", "plugin_configs", ["oauth_connection_id"])


def downgrade() -> None:
    if _index_exists("plugin_configs", "ix_plugin_configs_oauth_connection_id"):
        op.drop_index("ix_plugin_configs_oauth_connection_id", table_name="plugin_configs")
    if _column_exists("plugin_configs", "oauth_connection_id"):
        with op.batch_alter_table("plugin_configs") as batch_op:
            batch_op.drop_constraint(
                "fk_plugin_configs_oauth_connection_id_oauth_connections", type_="foreignkey"
            )
            batch_op.drop_column("oauth_connection_id")
