"""Add conflict-detection fields to sync_journal

Revision ID: 027
Revises: 026
Create Date: 2026-07-27

Adds compare-and-swap conflict detection to the sync journal (issue #543,
design doc §3.4): a writer now reports the `s3_version_id` it last saw for a
path (`base_version_id`); if that doesn't match the path's current HEAD
version at write time, the row is flagged `conflict=True` and
`loser_version_id` records the version its write silently superseded (S3
versioning still retains it). `conflict_copy_path` is filled in later, once
the working-copy indexer materializes that superseded content as a
`name (conflict YYYY-MM-DD).md` copy alongside the winner.
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
    if not _column_exists("sync_journal", "base_version_id"):
        op.add_column("sync_journal", sa.Column("base_version_id", sa.String(), nullable=True))
    if not _column_exists("sync_journal", "conflict"):
        op.add_column(
            "sync_journal",
            sa.Column("conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index("ix_sync_journal_conflict", "sync_journal", ["conflict"])
    if not _column_exists("sync_journal", "loser_version_id"):
        op.add_column("sync_journal", sa.Column("loser_version_id", sa.String(), nullable=True))
    if not _column_exists("sync_journal", "conflict_copy_path"):
        op.add_column("sync_journal", sa.Column("conflict_copy_path", sa.String(), nullable=True))


def downgrade() -> None:
    if _column_exists("sync_journal", "conflict_copy_path"):
        op.drop_column("sync_journal", "conflict_copy_path")
    if _column_exists("sync_journal", "loser_version_id"):
        op.drop_column("sync_journal", "loser_version_id")
    if _column_exists("sync_journal", "conflict"):
        op.drop_index("ix_sync_journal_conflict", table_name="sync_journal")
        op.drop_column("sync_journal", "conflict")
    if _column_exists("sync_journal", "base_version_id"):
        op.drop_column("sync_journal", "base_version_id")
