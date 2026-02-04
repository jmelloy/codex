"""Add file_events table for event queue

Revision ID: 009
Revises: 008
Create Date: 2026-02-04

This migration adds:
- file_events table for queueing file operations
  used by the event worker for async processing with batched git commits
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create file_events table
    if not table_exists("file_events"):
        op.create_table(
            "file_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("notebook_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="pending"),
            sa.Column("operation", sa.Text(), nullable=False),
            sa.Column("correlation_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_file_events_notebook_id"),
            "file_events",
            ["notebook_id"],
        )
        op.create_index(
            op.f("ix_file_events_event_type"),
            "file_events",
            ["event_type"],
        )
        op.create_index(
            "ix_file_events_notebook_status",
            "file_events",
            ["notebook_id", "status"],
        )
        op.create_index(
            "ix_file_events_correlation",
            "file_events",
            ["correlation_id"],
        )
        op.create_index(
            "ix_file_events_created_at",
            "file_events",
            ["created_at"],
        )


def downgrade() -> None:
    # Drop file_events table
    if table_exists("file_events"):
        op.drop_index("ix_file_events_created_at", table_name="file_events")
        op.drop_index("ix_file_events_correlation", table_name="file_events")
        op.drop_index("ix_file_events_notebook_status", table_name="file_events")
        op.drop_index(op.f("ix_file_events_event_type"), table_name="file_events")
        op.drop_index(op.f("ix_file_events_notebook_id"), table_name="file_events")
        op.drop_table("file_events")
