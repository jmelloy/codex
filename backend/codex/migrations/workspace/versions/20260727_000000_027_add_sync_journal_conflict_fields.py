"""Add conflict-tracking fields to sync_journal

Revision ID: 027
Revises: 026
Create Date: 2026-07-27

Adds compare-and-swap conflict fields to `sync_journal` (issue #543, design
doc §3.4): `base_s3_version_id` is the version a writer reports having last
seen; when it no longer matches the latest journaled version for a path, the
new row is flagged `conflict=True` with `conflict_of_id` pointing at the row
it raced, and `conflict_copy_path` recording where the losing version was
materialized as a `name (conflict YYYY-MM-DD).ext` copy. Existing rows are
never mutated -- conflicts are recorded as new rows, so cursor-based readers
of the change feed always see them.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in result)
    inspector = sa.inspect(conn)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _column_exists("sync_journal", "base_s3_version_id"):
        op.add_column("sync_journal", sa.Column("base_s3_version_id", sa.String(), nullable=True))

    if not _column_exists("sync_journal", "conflict"):
        op.add_column(
            "sync_journal", sa.Column("conflict", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    if not _column_exists("sync_journal", "conflict_of_id"):
        op.add_column("sync_journal", sa.Column("conflict_of_id", sa.Integer(), nullable=True))
        with op.batch_alter_table("sync_journal") as batch_op:
            batch_op.create_foreign_key(
                "fk_sync_journal_conflict_of_id", "sync_journal", ["conflict_of_id"], ["id"]
            )
        # Batch mode recreates the table (SQLite has no native ALTER for FK/constraints),
        # which drops any index created beforehand -- so indexes must run after the batch block.
        op.create_index("ix_sync_journal_conflict_of_id", "sync_journal", ["conflict_of_id"])

    if not _column_exists("sync_journal", "conflict_copy_path"):
        op.add_column("sync_journal", sa.Column("conflict_copy_path", sa.String(), nullable=True))

    if not _column_exists("sync_journal", "resolved_at"):
        op.add_column("sync_journal", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    if not _column_exists("sync_journal", "resolved_by_id"):
        op.add_column("sync_journal", sa.Column("resolved_by_id", sa.Integer(), nullable=True))
        with op.batch_alter_table("sync_journal") as batch_op:
            batch_op.create_foreign_key("fk_sync_journal_resolved_by_id", "users", ["resolved_by_id"], ["id"])

    op.create_index("ix_sync_journal_conflict", "sync_journal", ["conflict"])


def downgrade() -> None:
    if _column_exists("sync_journal", "conflict"):
        op.drop_index("ix_sync_journal_conflict", table_name="sync_journal")

    if _column_exists("sync_journal", "resolved_by_id"):
        with op.batch_alter_table("sync_journal") as batch_op:
            batch_op.drop_constraint("fk_sync_journal_resolved_by_id", type_="foreignkey")
        op.drop_column("sync_journal", "resolved_by_id")

    if _column_exists("sync_journal", "resolved_at"):
        op.drop_column("sync_journal", "resolved_at")

    if _column_exists("sync_journal", "conflict_copy_path"):
        op.drop_column("sync_journal", "conflict_copy_path")

    if _column_exists("sync_journal", "conflict_of_id"):
        op.drop_index("ix_sync_journal_conflict_of_id", table_name="sync_journal")
        with op.batch_alter_table("sync_journal") as batch_op:
            batch_op.drop_constraint("fk_sync_journal_conflict_of_id", type_="foreignkey")
        op.drop_column("sync_journal", "conflict_of_id")

    if _column_exists("sync_journal", "conflict"):
        op.drop_column("sync_journal", "conflict")

    if _column_exists("sync_journal", "base_s3_version_id"):
        op.drop_column("sync_journal", "base_s3_version_id")
