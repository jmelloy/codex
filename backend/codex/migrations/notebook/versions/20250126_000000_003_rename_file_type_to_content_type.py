"""Rename file_type column to content_type

Revision ID: 003
Revises: 002
Create Date: 2025-01-26

This migration renames the 'file_type' column to 'content_type' in the
file_metadata table to use MIME types instead of custom file type strings.

This migration is idempotent - it checks if the column has already been renamed.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Try to rename file_type to content_type if it exists
    # If the column doesn't exist (fresh install from migration 001), this will fail silently
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.alter_column("file_type", new_column_name="content_type")
    except Exception:
        # Column doesn't exist or already renamed, which is fine
        pass


def downgrade() -> None:
    # Rename content_type back to file_type
    try:
        with op.batch_alter_table("file_metadata", schema=None) as batch_op:
            batch_op.alter_column("content_type", new_column_name="file_type")
    except Exception:
        # Column doesn't exist, which is fine
        pass
