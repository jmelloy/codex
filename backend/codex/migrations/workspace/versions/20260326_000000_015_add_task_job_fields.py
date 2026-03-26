"""Add job_id and job_type fields to tasks table

Revision ID: 015
Revises: 014
Create Date: 2026-03-26

Adds job_id (ARQ job identifier) and job_type (generic dispatch type) columns
to the tasks table for background task execution support.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("job_id", sa.String(), nullable=True))
    op.add_column("tasks", sa.Column("job_type", sa.String(), nullable=False, server_default="agent"))


def downgrade() -> None:
    op.drop_column("tasks", "job_type")
    op.drop_column("tasks", "job_id")
