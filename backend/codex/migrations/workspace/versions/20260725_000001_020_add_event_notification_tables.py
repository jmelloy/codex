"""Add events, notifications and workspace_watches tables

Revision ID: 020
Revises: 019
Create Date: 2026-07-25

Adds the append-only Event outbox, the per-recipient Notification table, and
the WorkspaceWatch opt-in/mute preference table for async notification fanout
via ARQ (issue #530).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("kind", sa.String(), nullable=False, index=True),
        sa.Column("subject", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("event_id", "recipient_id", name="uq_notifications_event_recipient"),
    )

    op.create_table(
        "workspace_watches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_watches_workspace_user"),
    )


def downgrade() -> None:
    op.drop_table("workspace_watches")
    op.drop_table("notifications")
    op.drop_table("events")
