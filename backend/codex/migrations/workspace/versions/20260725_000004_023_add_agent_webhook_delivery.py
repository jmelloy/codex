"""Add agent webhook delivery config and audit table

Revision ID: 023
Revises: 022
Create Date: 2026-07-25

Adds `webhook_url`, `webhook_secret_encrypted`, and `webhook_max_retries` to
`agents`, and a new `agent_webhook_deliveries` audit table — the delivery
channel for external bots (issue #536, docs/design/multi-user-multi-org.md
§2.1 and §8 phase 3). Existing agents get NULL webhook config and default
`webhook_max_retries=5`, unaffected until an agent is switched to
`kind="external"` and configured with a webhook.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers
revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = inspect(conn)
    return any(col["name"] == column for col in inspector.get_columns(table))


def upgrade() -> None:
    if not _column_exists("agents", "webhook_url"):
        op.add_column("agents", sa.Column("webhook_url", sa.String(), nullable=True))
    if not _column_exists("agents", "webhook_secret_encrypted"):
        op.add_column("agents", sa.Column("webhook_secret_encrypted", sa.String(), nullable=True))
    if not _column_exists("agents", "webhook_max_retries"):
        op.add_column(
            "agents",
            sa.Column("webhook_max_retries", sa.Integer(), nullable=False, server_default="5"),
        )

    op.create_table(
        "agent_webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_webhook_deliveries")

    if _column_exists("agents", "webhook_max_retries"):
        op.drop_column("agents", "webhook_max_retries")
    if _column_exists("agents", "webhook_secret_encrypted"):
        op.drop_column("agents", "webhook_secret_encrypted")
    if _column_exists("agents", "webhook_url"):
        op.drop_column("agents", "webhook_url")
