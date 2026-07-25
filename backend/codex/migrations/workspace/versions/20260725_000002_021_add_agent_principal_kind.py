"""Add agents.kind and agents.principal_id

Revision ID: 021
Revises: 020
Create Date: 2026-07-25

Adds `kind` ("hosted" | "external") and `principal_id` (nullable FK to
`users.id`, unique) to `agents`, linking the agent "brain config" to a bot
principal identity (issue #534, docs/design/multi-user-multi-org.md §2.1).
Depends conceptually on `users.kind` from issue #533 (PR #568, not yet
merged) for distinguishing bot principals, but does not require it: existing
agents get `kind="hosted"` and `principal_id=NULL`, unaffected either way.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers
revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("agents", "kind"):
        op.add_column(
            "agents",
            sa.Column(
                "kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="hosted"
            ),
        )
    if not _column_exists("agents", "principal_id"):
        op.add_column("agents", sa.Column("principal_id", sa.Integer(), nullable=True))
        with op.batch_alter_table("agents") as batch_op:
            batch_op.create_foreign_key("fk_agents_principal_id_users", "users", ["principal_id"], ["id"])
            batch_op.create_unique_constraint("uq_agents_principal_id", ["principal_id"])
        # Batch mode recreates the table (SQLite has no native ALTER for FK/unique
        # constraints), which drops any index created beforehand — so this must
        # run after the batch block, against the final table.
        op.create_index("ix_agents_principal_id", "agents", ["principal_id"])


def downgrade() -> None:
    if _column_exists("agents", "principal_id"):
        with op.batch_alter_table("agents") as batch_op:
            batch_op.drop_constraint("uq_agents_principal_id", type_="unique")
            batch_op.drop_constraint("fk_agents_principal_id_users", type_="foreignkey")
        op.drop_index("ix_agents_principal_id", table_name="agents")
        op.drop_column("agents", "principal_id")
    if _column_exists("agents", "kind"):
        op.drop_column("agents", "kind")
