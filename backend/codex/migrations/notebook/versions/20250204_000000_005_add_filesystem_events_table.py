"""Add filesystem_events table for event queue

Revision ID: 005
Revises: 004
Create Date: 2025-02-04

This migration adds the filesystem_events table for queuing file system
operations. Events are batched and processed by the queue worker every 5 seconds
to prevent race conditions around moves and deletes.
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
    # Create filesystem_events table
    op.create_table(
        "filesystem_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("new_path", sa.String(), nullable=True),
        sa.Column("metadata", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for efficient queries
    with op.batch_alter_table("filesystem_events", schema=None) as batch_op:
        batch_op.create_index("ix_filesystem_events_event_type", ["event_type"])
        batch_op.create_index("ix_filesystem_events_status", ["status"])
        batch_op.create_index("ix_filesystem_events_created_at", ["created_at"])


def downgrade() -> None:
    # Drop indexes first
    with op.batch_alter_table("filesystem_events", schema=None) as batch_op:
        batch_op.drop_index("ix_filesystem_events_created_at")
        batch_op.drop_index("ix_filesystem_events_status")
        batch_op.drop_index("ix_filesystem_events_event_type")
    
    # Drop table
    op.drop_table("filesystem_events")
