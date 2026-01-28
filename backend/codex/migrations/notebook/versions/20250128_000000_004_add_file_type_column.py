"""Add file_type column for frontmatter type property

Revision ID: 004
Revises: 003
Create Date: 2025-01-28

This migration adds a new 'file_type' column to the file_metadata table
to store the 'type' property from frontmatter (e.g., "todo", "note", "view").
This is different from 'content_type' which stores MIME types.

The column is indexed for efficient filtering in dynamic views.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add file_type column if it doesn't exist
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.add_column(sa.Column("file_type", sa.String(), nullable=True))
            batch_op.create_index("ix_file_metadata_file_type", ["file_type"])
    except Exception:
        # Column already exists, which is fine
        pass


def downgrade() -> None:
    # Remove file_type column
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.drop_index("ix_file_metadata_file_type")
            batch_op.drop_column("file_type")
    except Exception:
        # Column doesn't exist, which is fine
        pass
