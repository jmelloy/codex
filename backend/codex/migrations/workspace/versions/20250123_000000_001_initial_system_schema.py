"""Initial system database schema

Revision ID: 001
Revises:
Create Date: 2025-01-23

This migration creates the initial schema for the system database:
- users: User accounts for authentication
- workspaces: Workspaces for organizing notebooks
- workspace_permissions: Permission mapping between users and workspaces
- tasks: Tasks for agent work
- notebooks: Notebook metadata

This migration is idempotent - it checks if tables exist before creating them.
This supports both fresh installations and existing databases that predate Alembic.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    # Create users table
    if not table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("theme_setting", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # Create workspaces table
    if not table_exists("workspaces"):
        op.create_table(
            "workspaces",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("theme_setting", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("path"),
        )
        op.create_index(op.f("ix_workspaces_name"), "workspaces", ["name"], unique=False)

    # Create workspace_permissions table
    if not table_exists("workspace_permissions"):
        op.create_table(
            "workspace_permissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("permission_level", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create tasks table
    if not table_exists("tasks"):
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("assigned_to", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create notebooks table
    if not table_exists("notebooks"):
        op.create_table(
            "notebooks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("path", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notebooks_name"), "notebooks", ["name"], unique=False)
        op.create_index(op.f("ix_notebooks_path"), "notebooks", ["path"], unique=False)
        op.create_index(op.f("ix_notebooks_workspace_id"), "notebooks", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notebooks_workspace_id"), table_name="notebooks")
    op.drop_index(op.f("ix_notebooks_path"), table_name="notebooks")
    op.drop_index(op.f("ix_notebooks_name"), table_name="notebooks")
    op.drop_table("notebooks")
    op.drop_table("tasks")
    op.drop_table("workspace_permissions")
    op.drop_index(op.f("ix_workspaces_name"), table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
