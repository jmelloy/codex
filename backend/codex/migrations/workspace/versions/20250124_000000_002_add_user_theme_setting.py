"""Add theme_setting column to users table

Revision ID: 002
Revises: 001
Create Date: 2025-01-24

This migration adds theme_setting to the users table for existing databases.
The initial schema (001) already includes this column for fresh installations.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add theme_setting column to users table if it doesn't exist
    if not column_exists("users", "theme_setting"):
        op.add_column(
            "users",
            sa.Column("theme_setting", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    if column_exists("users", "theme_setting"):
        op.drop_column("users", "theme_setting")
