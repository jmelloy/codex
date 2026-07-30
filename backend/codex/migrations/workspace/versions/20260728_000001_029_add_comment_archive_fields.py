"""Add archived_at/archived_by_id to comments

Revision ID: 029
Revises: 028
Create Date: 2026-07-28

Adds the archive fields a workspace admin sets when dismissing an orphaned
discussion thread from the orphaned-discussions view (issue #547) without
deleting or un-orphaning it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("comments", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("comments", sa.Column("archived_by_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("comments", "archived_by_id")
    op.drop_column("comments", "archived_at")
