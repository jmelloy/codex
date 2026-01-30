"""Add pages table for file-based pages

Revision ID: 005
Revises: 004
Create Date: 2026-01-30

This migration adds the 'pages' table to support file-based page organization.
Pages are directories containing numbered files (blocks) that form a structured document.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pages table."""
    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("directory_path", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notebook_id", "directory_path", name="uq_page_notebook_path"),
        sqlite_autoincrement=True,
    )
    
    # Create indexes for performance
    op.create_index("ix_pages_notebook_id", "pages", ["notebook_id"])
    op.create_index("ix_pages_directory_path", "pages", ["directory_path"])


def downgrade() -> None:
    """Remove pages table."""
    op.drop_index("ix_pages_directory_path", table_name="pages")
    op.drop_index("ix_pages_notebook_id", table_name="pages")
    op.drop_table("pages")
