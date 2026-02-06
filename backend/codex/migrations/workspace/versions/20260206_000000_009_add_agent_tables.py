"""Add AI agent tables

Revision ID: 009
Revises: 008
Create Date: 2026-02-06

This migration adds AI agent tables:
- agents: Agent configuration per workspace
- agent_credentials: Encrypted API keys for agents
- agent_sessions: Agent execution sessions
- agent_action_logs: Audit log for agent actions
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
    # Create agents table
    if not table_exists("agents"):
        op.create_table(
            "agents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workspace_id", sa.Integer(), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
            sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("scope", sa.JSON(), nullable=False),
            sa.Column("can_read", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("can_write", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("can_create", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("can_delete", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("can_execute_code", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("can_access_integrations", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("max_requests_per_hour", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("max_tokens_per_request", sa.Integer(), nullable=False, server_default="4000"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("system_prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agents_workspace_id"), "agents", ["workspace_id"])

    # Create agent_credentials table
    if not table_exists("agent_credentials"):
        op.create_table(
            "agent_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("agent_id", sa.Integer(), nullable=False),
            sa.Column("key_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("encrypted_value", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agent_credentials_agent_id"), "agent_credentials", ["agent_id"])

    # Create agent_sessions table
    if not table_exists("agent_sessions"):
        op.create_table(
            "agent_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("agent_id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("context", sa.JSON(), nullable=False),
            sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("api_calls_made", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("files_modified", sa.JSON(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agent_sessions_agent_id"), "agent_sessions", ["agent_id"])

    # Create agent_action_logs table
    if not table_exists("agent_action_logs"):
        op.create_table(
            "agent_action_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("target_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("input_summary", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("output_summary", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column("was_allowed", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("execution_time_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_agent_action_logs_session_id"), "agent_action_logs", ["session_id"])


def downgrade() -> None:
    if table_exists("agent_action_logs"):
        op.drop_index(op.f("ix_agent_action_logs_session_id"), table_name="agent_action_logs")
        op.drop_table("agent_action_logs")

    if table_exists("agent_sessions"):
        op.drop_index(op.f("ix_agent_sessions_agent_id"), table_name="agent_sessions")
        op.drop_table("agent_sessions")

    if table_exists("agent_credentials"):
        op.drop_index(op.f("ix_agent_credentials_agent_id"), table_name="agent_credentials")
        op.drop_table("agent_credentials")

    if table_exists("agents"):
        op.drop_index(op.f("ix_agents_workspace_id"), table_name="agents")
        op.drop_table("agents")
