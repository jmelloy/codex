"""Add job_id and job_type fields to tasks table

Revision ID: 016
Revises: 015
Create Date: 2026-03-27

Adds job_id (ARQ job identifier) and job_type (generic dispatch type) columns
to the tasks table for background task execution support.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("tasks", "job_id"):
        op.add_column("tasks", sa.Column("job_id", sa.String(), nullable=True))
    if not _column_exists("tasks", "job_type"):
        op.add_column("tasks", sa.Column("job_type", sa.String(), nullable=False, server_default="agent"))


def downgrade() -> None:
    op.drop_column("tasks", "job_type")
    op.drop_column("tasks", "job_id")
