"""Add users.kind, display_name, avatar_url, bot_owner_org_id

Revision ID: 021
Revises: 020
Create Date: 2026-07-25

Adds the Principal model fields from issue #533: `kind` distinguishes human
users from bot service accounts, `display_name`/`avatar_url` are shared
profile fields, and `bot_owner_org_id` is a nullable placeholder for the org
that owns a bot (null for humans; orgs don't exist yet so this isn't a FK).
Also relaxes `hashed_password` to nullable since bots authenticate exclusively
via PATs and never have a password.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers
revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    if not _column_exists("users", "kind"):
        op.add_column(
            "users",
            sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default="human"),
        )
        op.create_index("ix_users_kind", "users", ["kind"])
    if not _column_exists("users", "display_name"):
        op.add_column("users", sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    if not _column_exists("users", "avatar_url"):
        op.add_column("users", sa.Column("avatar_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    if not _column_exists("users", "bot_owner_org_id"):
        op.add_column("users", sa.Column("bot_owner_org_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("hashed_password", existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("hashed_password", existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=False)

    if _column_exists("users", "bot_owner_org_id"):
        op.drop_column("users", "bot_owner_org_id")
    if _column_exists("users", "avatar_url"):
        op.drop_column("users", "avatar_url")
    if _column_exists("users", "display_name"):
        op.drop_column("users", "display_name")
    if _column_exists("users", "kind"):
        op.drop_index("ix_users_kind", table_name="users")
        op.drop_column("users", "kind")
