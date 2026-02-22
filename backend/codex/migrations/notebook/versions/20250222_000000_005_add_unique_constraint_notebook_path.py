"""Add unique constraint on (notebook_id, path) to file_metadata

Revision ID: 005
Revises: 004
Create Date: 2025-02-22

This migration adds a unique constraint on (notebook_id, path) to the
file_metadata table. The model already defines this constraint, but it
was missing from the initial migration, allowing duplicate entries to
be created during race conditions between the filesystem observer and
background indexing.

Before adding the constraint, any existing duplicates are cleaned up
by keeping only the most recently updated row for each (notebook_id, path).
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
    # First, clean up any duplicate rows that may exist.
    # Keep only the row with the highest id for each (notebook_id, path) pair.
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            DELETE FROM file_metadata
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM file_metadata
                GROUP BY notebook_id, path
            )
        """)
    )

    # Now add the unique constraint using batch mode (required for SQLite)
    with op.batch_alter_table("file_metadata", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_file_metadata_notebook_path", ["notebook_id", "path"])


def downgrade() -> None:
    with op.batch_alter_table("file_metadata", schema=None) as batch_op:
        batch_op.drop_constraint("uq_file_metadata_notebook_path", type_="unique")
