"""Add refresh_tokens table for token refresh

Revision ID: 005_add_refresh_tokens_table
Revises: 004_add_markdown_files_table
Create Date: 2025-12-23

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_refresh_tokens_table"
down_revision = "004_add_markdown_files_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add refresh_tokens table."""
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("idx_refresh_tokens_token", "refresh_tokens", ["token"], unique=False)
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    """Remove refresh_tokens table."""
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
