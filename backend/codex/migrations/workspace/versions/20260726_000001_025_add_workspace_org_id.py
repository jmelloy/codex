"""Add workspaces.org_id and org-scoped slug uniqueness

Revision ID: 025
Revises: 024
Create Date: 2026-07-26

Adds `org_id` (nullable FK to `organizations.id`) and `org_member_default_level`
to `workspaces` (issue #538, docs/design/multi-user-multi-org.md §2.2/§2.3).
`org_id IS NULL` keeps today's personal-workspace behavior unchanged. The old
global `uq_workspaces_owner_slug` constraint is replaced with two partial
unique indexes so personal and org workspaces never contend for the same
uniqueness scope:
  - `uq_workspaces_owner_slug` on (owner_id, slug) WHERE org_id IS NULL
  - `uq_workspaces_org_slug` on (org_id, slug) WHERE org_id IS NOT NULL
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers
revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("workspaces", "org_id"):
        op.add_column("workspaces", sa.Column("org_id", sa.Integer(), nullable=True))
        with op.batch_alter_table("workspaces") as batch_op:
            batch_op.drop_constraint("uq_workspaces_owner_slug", type_="unique")
            batch_op.create_foreign_key("fk_workspaces_org_id_organizations", "organizations", ["org_id"], ["id"])
        # Batch mode recreates the table (SQLite has no native ALTER for FK/constraints),
        # which drops any index created beforehand -- so indexes must run after the batch block.
        op.create_index("ix_workspaces_org_id", "workspaces", ["org_id"])
        op.create_index(
            "uq_workspaces_owner_slug",
            "workspaces",
            ["owner_id", "slug"],
            unique=True,
            sqlite_where=sa.text("org_id IS NULL"),
            postgresql_where=sa.text("org_id IS NULL"),
        )
        op.create_index(
            "uq_workspaces_org_slug",
            "workspaces",
            ["org_id", "slug"],
            unique=True,
            sqlite_where=sa.text("org_id IS NOT NULL"),
            postgresql_where=sa.text("org_id IS NOT NULL"),
        )

    if not _column_exists("workspaces", "org_member_default_level"):
        op.add_column(
            "workspaces",
            sa.Column(
                "org_member_default_level",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="read",
            ),
        )


def downgrade() -> None:
    if _column_exists("workspaces", "org_member_default_level"):
        op.drop_column("workspaces", "org_member_default_level")

    if _column_exists("workspaces", "org_id"):
        op.drop_index("uq_workspaces_org_slug", table_name="workspaces")
        op.drop_index("uq_workspaces_owner_slug", table_name="workspaces")
        op.drop_index("ix_workspaces_org_id", table_name="workspaces")
        with op.batch_alter_table("workspaces") as batch_op:
            batch_op.drop_constraint("fk_workspaces_org_id_organizations", type_="foreignkey")
            batch_op.create_unique_constraint("uq_workspaces_owner_slug", ["owner_id", "slug"])
        op.drop_column("workspaces", "org_id")
