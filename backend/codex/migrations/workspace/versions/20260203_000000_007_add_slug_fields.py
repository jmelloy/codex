"""Add slug fields to workspace and notebook tables

Revision ID: 007
Revises: 006
Create Date: 2026-02-03

This migration adds:
- slug column to workspaces table (unique, indexed)
- slug column to notebooks table (indexed, unique per workspace)
- Populates slugs from existing path/name data
"""

from collections.abc import Sequence
import re
from pathlib import Path

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "item"


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add slug columns and populate them."""
    conn = op.get_bind()
    
    # Add slug column to workspaces table
    if not column_exists("workspaces", "slug"):
        # Add column as nullable first
        op.add_column(
            "workspaces",
            sa.Column(
                "slug",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
        )
        
        # Populate slugs from path (last component of filesystem path)
        workspaces = conn.execute(sa.text("SELECT id, path FROM workspaces")).fetchall()
        for workspace_id, path in workspaces:
            # Extract last component of path as slug
            slug = Path(path).name
            # Ensure it's a valid slug
            slug = slugify(slug) if slug else f"workspace-{workspace_id}"
            conn.execute(
                sa.text("UPDATE workspaces SET slug = :slug WHERE id = :id"),
                {"slug": slug, "id": workspace_id}
            )
        
        # Make column non-nullable and add unique constraint
        op.alter_column("workspaces", "slug", nullable=False)
        op.create_unique_constraint("uq_workspaces_slug", "workspaces", ["slug"])
        op.create_index("ix_workspaces_slug", "workspaces", ["slug"])
    
    # Add slug column to notebooks table
    if not column_exists("notebooks", "slug"):
        # Add column as nullable first
        op.add_column(
            "notebooks",
            sa.Column(
                "slug",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
        )
        
        # Populate slugs from path field (which is already a relative path/slug)
        notebooks = conn.execute(sa.text("SELECT id, path, workspace_id FROM notebooks")).fetchall()
        for notebook_id, path, workspace_id in notebooks:
            # Use the path field directly as it's already a slug-like value
            slug = slugify(path) if path else f"notebook-{notebook_id}"
            conn.execute(
                sa.text("UPDATE notebooks SET slug = :slug WHERE id = :id"),
                {"slug": slug, "id": notebook_id}
            )
        
        # Make column non-nullable and add unique constraint per workspace
        op.alter_column("notebooks", "slug", nullable=False)
        op.create_unique_constraint(
            "uq_notebooks_workspace_slug",
            "notebooks",
            ["workspace_id", "slug"]
        )
        op.create_index("ix_notebooks_slug", "notebooks", ["slug"])


def downgrade() -> None:
    """Remove slug columns."""
    # Remove notebook slug
    if column_exists("notebooks", "slug"):
        op.drop_index("ix_notebooks_slug", table_name="notebooks")
        op.drop_constraint("uq_notebooks_workspace_slug", "notebooks", type_="unique")
        op.drop_column("notebooks", "slug")
    
    # Remove workspace slug
    if column_exists("workspaces", "slug"):
        op.drop_index("ix_workspaces_slug", table_name="workspaces")
        op.drop_constraint("uq_workspaces_slug", "workspaces", type_="unique")
        op.drop_column("workspaces", "slug")
