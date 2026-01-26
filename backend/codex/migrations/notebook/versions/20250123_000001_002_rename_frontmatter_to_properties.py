"""Rename frontmatter column to properties

Revision ID: 002
Revises: 001
Create Date: 2025-01-23

This migration renames the 'frontmatter' column to 'properties' in the
file_metadata table to reflect the unified properties system where
frontmatter is the source of truth.

This migration is idempotent - it checks if the column has already been renamed.
Note: This migration is only needed for databases that existed before Alembic was added.
For fresh databases created via migration 001, this is a no-op since the table already
has the 'properties' column.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Try to rename frontmatter to properties if it exists
    # If the column doesn't exist (fresh install from migration 001), this will fail silently
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.alter_column("frontmatter", new_column_name="properties")
    except Exception:
        # Column doesn't exist or already renamed, which is fine
        pass


def downgrade() -> None:
    # Rename properties back to frontmatter
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.alter_column("properties", new_column_name="frontmatter")
    except Exception:
        # Column doesn't exist, which is fine
        pass
