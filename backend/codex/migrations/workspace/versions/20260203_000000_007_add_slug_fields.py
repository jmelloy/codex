"""Add slug fields to workspaces and notebooks

Revision ID: 007
Revises: 006
Create Date: 2026-02-03

This migration adds slug fields to workspaces and notebooks tables
for URL-friendly paths.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add slug columns to workspaces and notebooks tables."""
    # Add slug column to workspaces table if it doesn't exist
    if not column_exists("workspaces", "slug"):
        # SQLite doesn't support ALTER COLUMN, so we need to add the column as nullable first
        op.add_column(
            "workspaces",
            sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
        )
        # Populate slugs for existing workspaces from their names
        conn = op.get_bind()
        conn.execute(sa.text("""
            UPDATE workspaces 
            SET slug = REPLACE(REPLACE(REPLACE(LOWER(name), ' ', '-'), '_', '-'), '/', '-')
            WHERE slug = ''
        """))
        # Create unique index
        op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    # Add slug column to notebooks table if it doesn't exist
    if not column_exists("notebooks", "slug"):
        # SQLite doesn't support ALTER COLUMN, so we need to add the column as nullable first
        op.add_column(
            "notebooks",
            sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=""),
        )
        # Populate slugs for existing notebooks from their paths
        conn = op.get_bind()
        conn.execute(sa.text("""
            UPDATE notebooks 
            SET slug = path
            WHERE slug = ''
        """))
        # Create index (not unique as slugs are unique per workspace)
        op.create_index("ix_notebooks_slug", "notebooks", ["slug"], unique=False)


def downgrade() -> None:
    """Remove slug columns from workspaces and notebooks tables."""
    # Drop indexes first
    if column_exists("workspaces", "slug"):
        op.drop_index("ix_workspaces_slug", table_name="workspaces")
        op.drop_column("workspaces", "slug")
    
    if column_exists("notebooks", "slug"):
        op.drop_index("ix_notebooks_slug", table_name="notebooks")
        op.drop_column("notebooks", "slug")
