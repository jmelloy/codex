"""Add users table for authentication

Revision ID: 003_add_users_table
Revises: 002_remove_entry_artifact_tables
Create Date: 2025-12-22

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_users_table"
down_revision = "002_remove_entry_artifact_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add users table."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("workspace_path", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=False)
    op.create_index("idx_users_email", "users", ["email"], unique=False)


def downgrade() -> None:
    """Remove users table."""
    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_username", table_name="users")
    op.drop_table("users")
