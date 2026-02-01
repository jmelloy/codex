"""Add content_type column to integration_artifacts

Revision ID: 006
Revises: 005
Create Date: 2026-02-01

This migration adds:
- content_type column to integration_artifacts table to track MIME type
  of cached artifacts (not all artifacts are JSON)
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add content_type column with default value for existing rows
    if not column_exists("integration_artifacts", "content_type"):
        op.add_column(
            "integration_artifacts",
            sa.Column(
                "content_type",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=False,
                server_default="application/json",
            ),
        )


def downgrade() -> None:
    # Remove content_type column
    if column_exists("integration_artifacts", "content_type"):
        op.drop_column("integration_artifacts", "content_type")
