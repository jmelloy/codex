"""Add task_type and metadata columns to tasks table

Revision ID: 015
Revises: 014
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("tasks", "task_type"):
        op.add_column("tasks", sa.Column("task_type", sa.String(), nullable=True))
    if not _column_exists("tasks", "task_metadata"):
        op.add_column("tasks", sa.Column("task_metadata", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "task_metadata")
    op.drop_column("tasks", "task_type")
